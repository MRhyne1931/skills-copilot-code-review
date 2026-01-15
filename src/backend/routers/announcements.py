"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_active_announcements() -> List[Dict[str, Any]]:
    """
    Get all active announcements (within their date range)
    """
    current_time = datetime.utcnow().isoformat()
    
    # Query for active announcements
    query = {
        "expiration_date": {"$gte": current_time}
    }
    
    # Also check start_date if it exists
    query["$or"] = [
        {"start_date": {"$exists": False}},
        {"start_date": {"$lte": current_time}}
    ]
    
    announcements = []
    for announcement in announcements_collection.find(query).sort("created_at", -1):
        announcement["_id"] = str(announcement["_id"])
        announcements.append(announcement)
    
    return announcements


@router.get("/all", response_model=List[Dict[str, Any]])
def get_all_announcements(teacher_username: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """
    Get all announcements (including expired ones) - requires teacher authentication
    """
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")
    
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    announcements = []
    for announcement in announcements_collection.find().sort("created_at", -1):
        announcement["_id"] = str(announcement["_id"])
        announcements.append(announcement)
    
    return announcements


@router.post("", response_model=Dict[str, Any])
@router.post("/", response_model=Dict[str, Any])
def create_announcement(
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None,
    teacher_username: str = Query(...)
) -> Dict[str, Any]:
    """
    Create a new announcement - requires teacher authentication
    """
    # Check teacher authentication
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    # Validate dates
    try:
        expiration_dt = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if start_dt >= expiration_dt:
                raise HTTPException(
                    status_code=400, detail="Start date must be before expiration date")
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use ISO format.")
    
    # Create announcement
    announcement = {
        "message": message,
        "expiration_date": expiration_date,
        "created_by": teacher_username,
        "created_at": datetime.utcnow().isoformat()
    }
    
    if start_date:
        announcement["start_date"] = start_date
    
    result = announcements_collection.insert_one(announcement)
    announcement["_id"] = str(result.inserted_id)
    
    return announcement


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None,
    teacher_username: str = Query(...)
) -> Dict[str, Any]:
    """
    Update an existing announcement - requires teacher authentication
    """
    # Check teacher authentication
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    # Validate dates
    try:
        expiration_dt = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if start_dt >= expiration_dt:
                raise HTTPException(
                    status_code=400, detail="Start date must be before expiration date")
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use ISO format.")
    
    # Update announcement
    update_data = {
        "message": message,
        "expiration_date": expiration_date
    }
    
    if start_date:
        update_data["start_date"] = start_date
    else:
        # Remove start_date if it was cleared
        announcements_collection.update_one(
            {"_id": ObjectId(announcement_id)},
            {"$unset": {"start_date": ""}}
        )
    
    result = announcements_collection.update_one(
        {"_id": ObjectId(announcement_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Fetch and return updated announcement
    announcement = announcements_collection.find_one({"_id": ObjectId(announcement_id)})
    announcement["_id"] = str(announcement["_id"])
    
    return announcement


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    teacher_username: str = Query(...)
) -> Dict[str, str]:
    """
    Delete an announcement - requires teacher authentication
    """
    # Check teacher authentication
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    result = announcements_collection.delete_one({"_id": ObjectId(announcement_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
