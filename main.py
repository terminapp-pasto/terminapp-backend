from fastapi import FastAPI

app = FastAPI(title="TerminAPP Backend")


@app.get("/")
def inicio():
    return {"mensaje": "Hello World desde el backend de TerminAPP"} 
