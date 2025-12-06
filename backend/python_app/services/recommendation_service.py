from config import Config
from huggingface_hub import InferenceClient
from services.schemas import BottleneckRequest
from services.models import Project, Recommendation
from services.db import db

# Initialize the client using the imported config attributes
client = InferenceClient(model=Config.MODEL_NAME, token=Config.HF_API_KEY)

def get_llm_chat_response(messages: list) -> str:
    """
    Takes a list of messages (the conversation history if present) and gets a response.
    """
    try:
        completion = client.chat_completion(
            messages=messages,
            temperature=0.7,
            top_p=0.9,
            max_tokens=2048,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error in get_llm_chat_response: {e}")
        raise

def get_all_recommendations(user_id):
    recs = (
        db.session.query(Recommendation, Project.project_name)
        .join(Project, Recommendation.project_id == Project.project_id)
        .filter(Recommendation.user_id == user_id)
        .order_by(Recommendation.created_at.desc())
        .all()
    )
    return recs

def save_recommendation(user_id: int, project_id: int, content: str, bottleneck_activity: str):
    project = db.session.query(Project).filter(
        Project.project_id == project_id,
        (Project.user_id == user_id) | (Project.assigned_bpo_id == user_id)
    ).first()

    new_recommendation = Recommendation(
        user_id=user_id,
        project_id=project_id,
        content=content,
        bottleneck_activity=bottleneck_activity
    )
    db.session.add(new_recommendation)
    db.session.commit()
    return new_recommendation

def delete_recommendation(recommendation_id: int, user_id: int) -> bool:
    """
    Deletes a saved recommendation from the database.
    """
    try:
        recommendation_to_delete = Recommendation.query.filter_by(
            recommendation_id=recommendation_id, 
            user_id=user_id
        ).first()
        if not recommendation_to_delete:
            print(f"Deletion failed: No recommendation found with ID {recommendation_id} for user {user_id}")
            return False
        
        db.session.delete(recommendation_to_delete)
        db.session.commit()
        return True

    except Exception as e:
        db.session.rollback()
        print(f"Error deleting recommendation {recommendation_id}: {e}")
        return False