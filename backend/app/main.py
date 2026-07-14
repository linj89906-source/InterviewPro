import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import interview, map, questions, user, resume, knowledge, chat
from app.models import *  # ensure all models imported
from app.services.knowledge_base import init_fts

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FTS5 full-text search
init_fts()

app = FastAPI(title='InterviewPro API', version='1.0.0')

# CORS: production reads from env, dev defaults to allow all
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(interview.router)
app.include_router(map.router)
app.include_router(questions.router)
app.include_router(user.router)
app.include_router(resume.router)
app.include_router(knowledge.router)
app.include_router(chat.router)

@app.get('/')
async def root():
    return {'status': 'ok', 'service': 'InterviewPro - AI 面试训练系统'}

@app.get('/api/health')
async def health():
    return {'status': 'healthy'}
