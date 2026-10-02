import os
os.environ["DATABASE_URL"]="sqlite:///./test_muletrace.db"
os.environ["DEMO_MODE"]="true"
import pytest
from fastapi.testclient import TestClient
from app.db import Base,engine,SessionLocal
from app.main import app
from app.models import Workspace,User,DetectionSettings
from app.auth import hash_password
from app.detection import DEFAULTS

@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine); db=SessionLocal(); w1=Workspace(name="Alpha");w2=Workspace(name="Beta");db.add_all([w1,w2]);db.flush();u1=User(workspace_id=w1.id,email="sup@test.local",name="Supervisor",password_hash=hash_password("StrongPass!1"),role="supervisor");u2=User(workspace_id=w2.id,email="other@test.local",name="Other",password_hash=hash_password("StrongPass!1"),role="supervisor");db.add_all([u1,u2]);db.flush();db.add_all([DetectionSettings(workspace_id=w1.id,version=1,config=DEFAULTS,created_by=u1.id),DetectionSettings(workspace_id=w2.id,version=1,config=DEFAULTS,created_by=u2.id)]);db.commit();db.close();yield;Base.metadata.drop_all(engine)
@pytest.fixture
def client(): return TestClient(app)
@pytest.fixture
def auth(client):
    r=client.post('/api/auth/login',json={'email':'sup@test.local','password':'StrongPass!1'});assert r.status_code==200
    return {'X-CSRF-Token':client.cookies.get('muletrace_csrf')}

