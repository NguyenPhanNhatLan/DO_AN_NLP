from datetime import datetime
import requests
import json
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from label_studio_sdk import LabelStudio, Client
import logging

#file này để load dữ liệu từ mongo --> label-studio 
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

LABEL_STUDIO_PROJECT_ID = 3
load_dotenv()

def get_mongodb_connection():
    try:
        return MongoClient(os.getenv('MONGODB_URI'))
    except Exception as e:
        logger.error(f"✗ Lỗi kết nối MongoDB: {e}")
        raise


def get_label_studio_connection():
    try:
        ls = LabelStudio(
            base_url=os.getenv('LABEL_STUDIO_URL'),
            api_key=os.getenv('LABEL_STUDIO_API_KEY')
        )
        return ls
    except Exception as e:
        logger.error(f"✗ Lỗi kết nối Label Studio: {e}")
        raise


def get_existing_mongo_ids(tasks):
    try:
        existing_tasks = tasks
        existing_ids = {
            task.get('meta', {}).get('mongodb_id') 
            for task in existing_tasks
            if task.get('meta', {}).get('mongodb_id')
        }
        logger.info(f"✓ Tìm thấy {len(existing_ids)} tasks đã tồn tại trong Label Studio")
        return existing_ids
    except Exception as e:
        logger.error(f"✗ Lỗi khi lấy existing tasks: {e}")
        return set()
    

def prepare_task_from_document(doc, mongo_id):
    description_raw = doc.get('description_raw', '')
    ingredient_raw = doc.get('ingredient_raw', '')
    usage_tip = doc.get('usage_tip', '')
    
    parts = [p.strip() for p in [description_raw, ingredient_raw, usage_tip] if p and p.strip()]
    
    if not parts:
        return None
    text = "\n\n".join(parts)
    task = {
        'data': {
            'text': text,
            'name': doc.get('name', 'Unknown'),
            'brand': doc.get('brand', 'Unknown')
        },
        'meta': {
            'mongodb_id': mongo_id,
            'synced_at': datetime.now().isoformat(),
            'url': doc.get('url', ''),
            'price': doc.get('price', '')
        }
    }
    return task

def sync_with_mongo(batch_size=100):
    try:
        mongodb_client = get_mongodb_connection()
        ls_client = get_label_studio_connection()
        
        tasks = ls_client.tasks.list(project= LABEL_STUDIO_PROJECT_ID).items
        existing_mongo_ids = get_existing_mongo_ids(tasks=tasks)
        db = mongodb_client[os.getenv('MONGODB_DATABASE')]
        collection = db[os.getenv('MONGODB_COLLECTION')]
        
        total_docs = collection.estimated_document_count()
        logger.info(f"✓ Tìm thấy {total_docs} documents trong MongoDB")
        documents = collection.find()
        tasks = []
        skipped = 0
        empty = 0
        
        for doc in documents:
            mongo_id = str(doc['_id'])
            
            if mongo_id in existing_mongo_ids:
                skipped += 1
                continue
            
            task = prepare_task_from_document(doc, mongo_id)
            
            if task is None:
                empty += 1
                continue
            
            tasks.append(task)
        
        logger.info(f"Tổng kết: {len(tasks)} tasks mới, {skipped} đã tồn tại, {empty} không có nội dung")

        if tasks:
            total_imported = 0
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i + batch_size]
                try:
                    ls_client.projects.import_tasks(id=LABEL_STUDIO_PROJECT_ID, request= batch)
                    total_imported += len(batch)
                    logger.info(f"✓ Đã import batch {i//batch_size + 1}: {len(batch)} tasks")
                except Exception as e:
                    logger.error(f"✗ Lỗi khi import batch {i//batch_size + 1}: {e}")
            
            logger.info(f"✓ Hoàn thành! Đã sync {total_imported}/{len(tasks)} tasks mới")
            return total_imported
        else:
            logger.info("✓ Không có task mới cần sync")
            return 0
            
    except Exception as e:
        logger.error(f"✗ Lỗi trong quá trình sync: {e}")
        raise
    finally:
        if 'collection' in locals():
            collection.database.client.close()
            logger.info("✓ Đã đóng kết nối MongoDB")


if __name__ == "__main__":
    try:
        synced_count = sync_with_mongo(batch_size=50)
        print(f"\n{'='*50}")
        print(f"THÀNH CÔNG: Đã đồng bộ {synced_count} tasks")
        print(f"{'='*50}")
    except Exception as e:
        print(f"\n{'='*50}")
        print(f"LỖI: {e}")
        print(f"{'='*50}")
        exit(1)