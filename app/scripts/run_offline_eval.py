import json
import logging
import asyncio
import sys
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.evaluator import EvaluatorService
from app.services.prompt_editor import PromptEditorService
from app.services.groq_provider import LLMClient
from app.repositories.prompt_repo import PromptRepository

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def load_conversations(file_path: str = "app/data/conversations.json"):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load conversations: {e}")
        return []

async def run_evaluation(db: Session, conversations: list, prompt_override=None):
    provider = LLMClient()
    evaluator = EvaluatorService(db, provider)
    
    all_results = []
    logger.info("Starting manual evaluation...")

    for conv in conversations:
        contact_id = conv.get("contact_id")
        messages = conv.get("conversation", [])
        messages.sort(key=lambda x: x.get("message_id", 0))
        
        history = []
        for i, msg in enumerate(messages):
            direction = msg.get("direction")
            text = msg.get("text")
            
            if direction == "in":
                real_reply = None
                for j in range(i + 1, len(messages)):
                    if messages[j].get("direction") == "out":
                        real_reply = messages[j].get("text")
                        break
                
                if real_reply:
                    res = await evaluator.evaluate_message(
                        user_message=text,
                        real_reply=real_reply,
                        context="\n".join(history),
                        prompt_override=prompt_override
                    )
                    all_results.append({
                        "user_message": text,
                        "predicted_reply": res["reply"],
                        "real_reply": real_reply,
                        "score": res["score"]
                    })
                history.append(f"User: {text}")
            else:
                history.append(f"AI: {text}")

    if not all_results:
        return 0.0, []

    avg_score = sum(r["score"] for r in all_results) / len(all_results)
    return avg_score, all_results

async def main():
    conversations = load_conversations()
    if not conversations:
        return

    db = SessionLocal()
    try:
        prompt_repo = PromptRepository(db)
        active_prompt = prompt_repo.get_active_prompt()
        if not active_prompt:
            logger.error("No active prompt found.")
            return

        # 1. Evaluate Current Prompt
        logger.info(f"Evaluating Active Prompt V{active_prompt.version}...")
        avg_score, results = await run_evaluation(db, conversations)
        logger.info(f"Average Score: {avg_score:.2f}")

        # 2. Ask for manual evolution
        print("\n--- Evaluation Complete ---")
        print(f"Current Avg Score: {avg_score:.2f}")
        
        evolve = input("Would you like to trigger prompt evolution based on weak examples? (y/n): ")
        if evolve.lower() == 'y':
            weak_examples = [r for r in results if r["score"] < 0.7]
            if not weak_examples:
                print("No weak examples found (all scores >= 0.7). Skipping evolution.")
                return

            logger.info("Triggering prompt rewrite...")
            provider = LLMClient()
            editor = PromptEditorService(db, provider)
            
            # Send sample of weak examples
            new_prompt_data = await editor.rewrite_prompt(active_prompt.content, weak_examples[:3])
            new_content = new_prompt_data["updated_prompt"]
            logger.info(f"Proposed Changes Reasoning: {new_prompt_data['reasoning']}")
            
            # 3. Create Draft
            latest_v = prompt_repo.get_latest_version()
            new_v = latest_v + 1
            draft = prompt_repo.create_prompt(
                version=new_v, 
                content=new_content, 
                is_active=False,
                parent_version_id=active_prompt.id
            )
            logger.info(f"Created Draft V{new_v}.")

            # 4. Sandbox Evaluation
            logger.info(f"Running sandbox evaluation for V{new_v}...")
            new_score, _ = await run_evaluation(db, conversations, prompt_override=draft)
            logger.info(f"New Score: {new_score:.2f} (Old: {avg_score:.2f})")

            if new_score > avg_score:
                activate = input(f"New score is better. Activate V{new_v} now? (y/n): ")
                if activate.lower() == 'y':
                    prompt_repo.activate_prompt(draft.id)
                    logger.info("Activated new version.")
                else:
                    logger.info("Activation skipped.")
            else:
                logger.info("New version did not improve performance. Kept as draft.")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
