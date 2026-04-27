import os
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, auth, firestore

app = FastAPI(title="Todo API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Firebase Admin SDK
# Ensure firebase_service_account.json is in the backend directory
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "firebase_service_account.json")

if os.path.exists(SERVICE_ACCOUNT_FILE):
    try:
        cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase Admin initialized successfully.")
    except Exception as e:
        print(f"Error initializing Firebase Admin: {e}")
        db = None
else:
    print(f"Warning: {SERVICE_ACCOUNT_FILE} not found. Firebase will fail to initialize.")
    db = None

def verify_token(authorization: str = Header(...)):
    """
    Dependency to verify Firebase ID Token in the Authorization header.
    Returns the user's uid.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = authorization.split("Bearer ")[1]
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token["uid"]
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

class TodoCreate(BaseModel):
    title: str
    description: str = ""
    completed: bool = False

class TodoUpdate(BaseModel):
    title: str = None
    description: str = None
    completed: bool = None

@app.post("/todos", response_model=dict)
def create_todo(todo: TodoCreate, uid: str = Depends(verify_token)):
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    doc_ref = db.collection("todos").document()
    todo_data = todo.dict()
    todo_data["user_id"] = uid
    doc_ref.set(todo_data)
    
    return {"id": doc_ref.id, **todo_data}

@app.get("/todos", response_model=list)
def get_todos(uid: str = Depends(verify_token)):
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    todos_ref = db.collection("todos").where("user_id", "==", uid).stream()
    todos = []
    for doc in todos_ref:
        todo_data = doc.to_dict()
        todo_data["id"] = doc.id
        todos.append(todo_data)
        
    return todos

@app.put("/todos/{todo_id}")
def update_todo(todo_id: str, todo_update: TodoUpdate, uid: str = Depends(verify_token)):
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    doc_ref = db.collection("todos").document(todo_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Todo not found")
        
    doc_data = doc.to_dict()
    if doc_data.get("user_id") != uid:
        raise HTTPException(status_code=403, detail="Not authorized to update this todo")
        
    # Only update fields that are provided
    update_data = {k: v for k, v in todo_update.dict().items() if v is not None}
    if update_data:
        doc_ref.update(update_data)
        
    return {"message": "Todo updated successfully"}

@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: str, uid: str = Depends(verify_token)):
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    doc_ref = db.collection("todos").document(todo_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Todo not found")
        
    if doc.to_dict().get("user_id") != uid:
        raise HTTPException(status_code=403, detail="Not authorized to delete this todo")
        
    doc_ref.delete()
    return {"message": "Todo deleted successfully"}
