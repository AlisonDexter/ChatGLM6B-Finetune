import os
import platform
import signal
from transformers import AutoTokenizer, AutoModel
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pyreadline
from docx import Document
from langchain.embeddings import HuggingFaceBgeEmbeddings
import os
from langchain.vectorstores import FAISS


os.environ['CUDA_VISIBLE_DEVICES']='0'

tokenizer = AutoTokenizer.from_pretrained("D:/Age/ChatGLM3_main/models/merge_lora_model", trust_remote_code=True)
model = AutoModel.from_pretrained("D:/Age/ChatGLM3_main/models/merge_lora_model", trust_remote_code=True).quantize(4).cuda()
model = model.eval()

os_name = platform.system()
clear_command = 'cls' if os_name == 'Windows' else 'clear'
stop_stream = False

conversation_history = {}



def main(question, user_id):
    # ***************** RAG *****************

    doc_path = "D:/Age_copy/law_doc"
    documents = []
    def load_docx(file_path):
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        return text

    for file_name in os.listdir(doc_path):
        if file_name.endswith(".docx"):
            file_path = os.path.join(doc_path,file_name)
            try:
                text = load_docx(file_path)
                documents.append(text)
            except Exception as e:
                print(f"读取{file_name}失败:{e}")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=512,chunk_overlap=50)
    docs = text_splitter.create_documents(documents)
    print(f"成功载入{len(docs)}个文档块")
    # Step 3 Convert Documnets into Embeddings
    embedding_model = HuggingFaceBgeEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vector_store = FAISS.from_documents(docs,embedding_model)
    vector_store = FAISS.from_documents(docs,embedding_model)
    vector_store.save_local("faiss_index")
    print("文档已存入FAISS向量数据库")
    def rag_ask(query):
        max_lenght=60
        retrieved_docs = vector_store.similarity_search(query, k=3)
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        prompt = f"以下是相关资料：\n{context}\n\n用户问题:{query}\n\n请根据以下资料回答用户问题："
        return prompt

    # ***************** RAG *****************
  
    global conversation_history
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    
    history = conversation_history[user_id]
    query = str(question)
    prompt=rag_ask(query)
    response, history = model.chat(tokenizer, prompt, history=history)
    conversation_history[user_id] = history
    return response  # 只返回模型的回答，不包括用户的问题

