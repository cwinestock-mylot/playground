import variables
import os
import concurrent
import sys
import random
from openai import OpenAI
from tqdm import tqdm

"""
Creates a new vector store in OpenAI and uploads all html docs in data/cleaned_docs
into that vector store. 
NB any existing OpenAI vector store is first deleted to prevent confusion.

There are 286 guideline pages. To reduce the OpenAI cost and time when running queries, I
have only uploaded 10 guidelines plus the correct one
www.rch.org.au⧸clinicalguide⧸guideline_index⧸croup_laryngotracheobronchitis.html

"""

client = OpenAI(api_key=variables.OpenAI.api_key)
random.seed(10)


def set_up_vector_store():
    htmls_path = os.path.join(variables.DATA_DIR, 'cleaned_docs')

    # delete any existing vector stores
    delete_all_vector_stores()

    store_name = "heidi_demo"
    vector_store = create_vector_store(store_name)

    upload_html_files_to_vector_store(vector_store.id, htmls_path)

    return vector_store


def create_vector_store(store_name: str):
    try:
        vector_store = client.vector_stores.create(name=store_name)
        print("Vector store created. id:", vector_store.id)
        return vector_store
    except Exception as e:
        print(f"Error creating vector store: {e}. Fix and re-run script.")
        sys.exit(1)


def upload_html_files_to_vector_store(vector_store_id: str, htmls_path: str):
    """
    Uploads all .html files in the path htmls_path to the OpenAI vector store.
    The uploading is done concurrently to save time.

    :param vector_store_id: the id of the vector store to use
    :param htmls_path: the folder path containing the html files to upload
    :return: nothing
    """
    html_files = [os.path.join(htmls_path, f) for f in os.listdir(htmls_path) if f.endswith('.html')]

    # select a random sample of 10 guidelines. Make sure to add the obligatory guideline
    # for the demo example to work.
    # html_files = random.sample(html_files, 100)
    obligatory_file = "www.rch.org.au⧸clinicalguide⧸guideline_index⧸croup_laryngotracheobronchitis.html"

    obligatory_path = os.path.join(variables.CLEANED_DOCS_DIR, obligatory_file)
    if obligatory_path not in html_files:
        html_files.append(obligatory_path)

    print(f"{len(html_files)} html docs to process. Uploading in parallel...")
    stats = {"total_files": len(html_files), "successful_uploads": 0, "failed_uploads": 0, "errors": []}

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(upload_single_doc, file_path, vector_store_id): file_path
                   for file_path in html_files}
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(html_files)):
            result = future.result()
            if result["status"] == "success":
                stats["successful_uploads"] += 1
            else:
                stats["failed_uploads"] += 1
                stats["errors"].append(result)

    print('stats\n', stats)

    response = client.vector_stores.files.list(vector_store_id)
    # files = response.data
    return stats


def upload_single_doc(file_path: str, vector_store_id: str):
    file_name = os.path.basename(file_path)
    try:
        file_response = client.files.create(file=open(file_path, 'rb'), purpose="assistants")
        attach_response = client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_response.id
        )
        # print('file_response:', file_response)
        return {"file": file_name, "status": "success"}
    except Exception as e:
        print(f"Error with {file_name}: {str(e)}")
        return {"file": file_name, "status": "failed", "error": str(e)}


def delete_all_vector_stores():
    vector_stores = client.vector_stores.list()
    print('Deleting all existing vector stores. Total number:', len(list(vector_stores)))
    for vector_store in tqdm(vector_stores, desc="deleting vector stores"):
        client.vector_stores.delete(vector_store_id=vector_store.id)
    vector_stores = client.vector_stores.list()
    print('New number of vector stores:', len(list(vector_stores)))


def fetch_vector_store():
    vector_stores = client.vector_stores.list()
    num_vector_stores = len(list(vector_stores))
    assert num_vector_stores == 1, f'There are {num_vector_stores}. There should be 1 only.'
    vector_store = list(vector_stores)[0]
    return vector_store
