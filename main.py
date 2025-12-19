import asyncio
from js import document, console, Uint8Array, File, Blob, URL, window
from pyodide.ffi import create_proxy
import io
import pypdf
import platform

# 儲存所有上傳的 PDF 檔案
files_store = []

# 取得 HTML 元素
file_input = document.getElementById("file-input")
file_list_container = document.getElementById("file-list-container")
merge_btn = document.getElementById("merge-btn")
status_div = document.getElementById("status")
download_link = document.getElementById("download-link")

def render_file_list():
    """更新檔案列表顯示"""
    file_list_container.innerHTML = ""

    # 沒有檔案時，顯示提示訊息
    if not files_store:
        status_div.innerText = "準備就緒 (請選擇檔案)"
        file_list_container.innerHTML = "<div style='color:#ccc; padding:10px; text-align:center;'>尚未選擇檔案</div>"
        return
    else:
        status_div.innerText = f"目前共有 {len(files_store)} 個檔案 (可拖拉排序)"

    for index, file_obj in enumerate(files_store):
        div = document.createElement("div")
        div.className = "file-item"
        
        # 拖拉把手圖示
        handle_span = document.createElement("span")
        handle_span.className = "drag-handle"
        handle_span.innerText = "☰"
        
        # 顯示檔案名稱和順序
        name_span = document.createElement("span")
        name_span.className = "file-name"
        name_span.innerText = f"{index + 1}. {file_obj['name']}"
        
        # 按鈕區塊
        btn_group = document.createElement("div")
        btn_group.className = "btn-group"

        # 刪除按鈕
        btn_del = document.createElement("button")
        btn_del.className = "btn-del"
        btn_del.innerText = "✕"
        btn_del.onclick = create_proxy(lambda e, idx=index: remove_item(idx))

        # 組合各元素
        div.appendChild(handle_span) # 先放把手
        div.appendChild(name_span)
        btn_group.appendChild(btn_del)
        div.appendChild(btn_group)
        
        file_list_container.appendChild(div)

# 拖拉排序完成後的處理函式
def on_reorder_handler(old_index, new_index):
    """更新檔案順序"""
    # 轉換為整數
    old_idx = int(old_index)
    new_idx = int(new_index)
    
    # 在列表中移動檔案
    item = files_store.pop(old_idx)
    files_store.insert(new_idx, item)
    
    # 重新繪製列表 (更新編號)
    render_file_list()

def remove_item(index):
    """刪除特定檔案"""
    del files_store[index]
    render_file_list()
    if not files_store:
        file_input.value = ""

# 新增檔案
async def add_files_handler(event):
    new_files = file_input.files
    if new_files.length == 0: return
    status_div.innerText = "讀取中..."
    for i in range(new_files.length):
        file = new_files.item(i)
        array_buffer = await file.arrayBuffer()
        py_bytes = array_buffer.to_py()
        files_store.append({'name': file.name, 'data': py_bytes})
    render_file_list()
    file_input.value = ""

# 合併 PDF
async def merge_handler(event):
    if not files_store:
        window.alert("請先加入 PDF 檔案！")
        return
    status_div.innerText = "🚀 正在合併，請稍候..."
    merge_btn.disabled = True
    try:
            # 建立 PDF 合併器
        writer = pypdf.PdfWriter()
        for file_obj in files_store:
            stream = io.BytesIO(file_obj['data'])
            reader = pypdf.PdfReader(stream)
            writer.append(reader)
            # 設定檔案資訊
        metadata = {
            '/Producer': f"Python {platform.python_version()} + pypdf {pypdf.__version__} (PyScript)",
            '/Title': 'Merged Document',
        }
        writer.add_metadata(metadata)
            # 準備下載檔案
        output_stream = io.BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)
        final_bytes = output_stream.getvalue()
        js_array = Uint8Array.new(len(final_bytes))
        js_array.assign(final_bytes)
        blob = Blob.new([js_array], {type: "application/pdf"})
        blob_url = URL.createObjectURL(blob)
        download_link.href = blob_url
        download_link.style.display = "block"
        status_div.innerText = "✅ 合併成功！"
    except Exception as e:
        console.error(e)
        status_div.innerText = f"❌ 錯誤: {str(e)}"
    finally:
        merge_btn.disabled = False

# 綁定事件監聽器
file_proxy = create_proxy(add_files_handler)
file_input.addEventListener("change", file_proxy)
merge_proxy = create_proxy(merge_handler)
merge_btn.addEventListener("click", merge_proxy)

# 將排序函式暴露給 JavaScript
window.py_on_reorder = create_proxy(on_reorder_handler)

# 初始化頁面
render_file_list()