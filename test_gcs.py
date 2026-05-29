import asyncio
from app.core.storage_service import storage_service
from fastapi import UploadFile

async def run():
    with open('.env', 'rb') as f_obj:
        f = UploadFile(filename='test.txt', file=f_obj)
        res = await storage_service.upload_file(f, 'Teste')
        print('Resultado:', res)

asyncio.run(run())
