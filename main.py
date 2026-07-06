from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Message": "Hello World! 这是我的错题本服务器！"}
