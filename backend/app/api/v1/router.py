from fastapi import APIRouter

from app.api.v1 import analysis, auth, documents, notes, profile, quiz, subjects

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(analysis.router)
api_router.include_router(notes.router)
api_router.include_router(subjects.router)
api_router.include_router(quiz.router)
api_router.include_router(profile.router)
