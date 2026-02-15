import sys
from pathlib import Path

# Add project root to sys.path to resolve app.* imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.database import SessionLocal
from app.models.prompt import Prompt


def seed():
    db = SessionLocal()
    try:
        # Check if any prompt exists
        existing_prompt = db.query(Prompt).first()
        if not existing_prompt:
            print("No prompts found. Seeding initial prompt...")
            initial_prompt = Prompt(
                version=1,
                content="You are a professional customer support AI. Respond clearly, politely, and concisely.",
                is_active=True,
            )
            db.add(initial_prompt)
            db.commit()
            print("Initial prompt version 1 created successfully.")
        else:
            print("Found existing prompts. Skipping seed.")
    except Exception as e:
        print(f"An error occurred while seeding: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
