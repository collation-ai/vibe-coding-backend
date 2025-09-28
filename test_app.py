from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

@app.get("/")
def root():
    return {"message": "API is running", "time": datetime.utcnow().isoformat()}

@app.get("/test")
def test():
    return {"status": "OK", "python": "3.11"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)