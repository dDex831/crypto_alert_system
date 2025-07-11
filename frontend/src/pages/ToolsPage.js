import React, { useEffect, useState, useRef } from "react";
import { Modal, Button, Form } from "react-bootstrap";

export default function ToolsPage() {
  const [notes, setNotes] = useState([]);
  const [show, setShow] = useState(false);
  const [currentNote, setCurrentNote] = useState({
    id: "",
    title: "",
    code: "",
    purpose: "",
    result: "",
  });

  const codeRef = useRef(null);

  const loadNotes = async () => {
    const res = await fetch("/api/notes");
    const data = await res.json();
    setNotes(data);
  };

  // ⭐ 綁定貼圖事件
  useEffect(() => {
    loadNotes();

    const el = codeRef.current;
    if (el) {
      el.addEventListener("paste", handlePaste);
    }

    return () => {
      if (el) {
        el.removeEventListener("paste", handlePaste);
      }
    };
  }, [show]); // 等 Modal 顯示後才能綁定 codeRef

  const handleShowModal = (note) => {
    setCurrentNote(note || { id: "", title: "", code: "", purpose: "", result: "" });
    setShow(true);
  };

  const handleDelete = async (id) => {
    if (window.confirm("確定要刪除此筆記嗎？")) {
      await fetch(`/api/notes/${id}`, { method: "DELETE" });
      loadNotes();
    }
  };

  // ⭐ 處理貼上圖片事件（拖曳圖片大小）
  const handlePaste = async (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (const item of items) {
      if (item.kind === "file" && item.type.startsWith("image/")) {
        const file = item.getAsFile();
        const reader = new FileReader();

        reader.onload = async (event) => {
          const base64 = event.target.result;
          const tempId = "img_" + Date.now();

          // 插入圖片容器，可拖曳調整大小
          document.execCommand(
            "insertHTML",
            false,
            `
            <div contenteditable="false" style="display:inline-block; resize:both; overflow:auto; max-width:100%;">
              <img id="${tempId}" src="${base64}" style="width:100%; display:block;" />
            </div><br/>
            `
          );

          // 上傳圖片到伺服器
          try {
            const res = await fetch("/api/upload_image", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ image: base64 }),
            });
            const data = await res.json();
            if (data.url) {
              const img = document.getElementById(tempId);
              if (img) img.src = `/images/${data.url.split("/").pop()}`;
            } else {
              console.error("圖片上傳失敗", data);
            }
          } catch (err) {
            console.error("圖片上傳錯誤", err);
          }
        };

        reader.readAsDataURL(file);
        e.preventDefault();
        break;
      }
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    const htmlContent = codeRef.current.innerHTML;
    const method = currentNote.id ? "PUT" : "POST";
    const url = currentNote.id ? `/api/notes/${currentNote.id}` : "/api/notes";
    await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...currentNote, code: htmlContent }),
    });
    setShow(false);
    loadNotes();
  };

  return (
    <section>
      <h3>筆記管理</h3>
      <Button variant="success" className="mb-3" onClick={() => handleShowModal()}>
        新增筆記
      </Button>
      <div>
        {notes.map((n) => (
          <div className="card mb-2" key={n.id}>
            <div className="card-body d-flex justify-content-between align-items-center">
              <span>{n.title}</span>
              <div>
                <Button variant="info" size="sm" className="me-1" onClick={() => handleShowModal(n)}>
                  編輯
                </Button>
                <Button variant="danger" size="sm" onClick={() => handleDelete(n.id)}>
                  刪除
                </Button>
              </div>
            </div>
            <div className="card-body" style={{ whiteSpace: "pre-wrap" }}>
              <strong>程式碼：</strong>
              <div dangerouslySetInnerHTML={{ __html: n.code }} />
              <strong>目的：</strong>
              <div>{n.purpose}</div>
              <strong>結果：</strong>
              <div>{n.result}</div>
            </div>
          </div>
        ))}
      </div>

      <Modal show={show} onHide={() => setShow(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>新增 / 編輯 筆記</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSave}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>標題</Form.Label>
              <Form.Control
                value={currentNote.title}
                onChange={(e) => setCurrentNote({ ...currentNote, title: e.target.value })}
                required
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>程式碼 (可貼圖片)</Form.Label>
              <div
                ref={codeRef}
                contentEditable
                className="form-control"
                style={{
                  minHeight: "150px",
                  resize: "vertical",
                  overflow: "auto",
                  whiteSpace: "pre-wrap",
                }}
                dangerouslySetInnerHTML={{ __html: currentNote.code }}
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>目的</Form.Label>
              <Form.Control
                as="textarea"
                rows={2}
                value={currentNote.purpose}
                onChange={(e) => setCurrentNote({ ...currentNote, purpose: e.target.value })}
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>結果</Form.Label>
              <Form.Control
                as="textarea"
                rows={2}
                value={currentNote.result}
                onChange={(e) => setCurrentNote({ ...currentNote, result: e.target.value })}
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShow(false)}>
              取消
            </Button>
            <Button variant="primary" type="submit">
              儲存
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </section>
  );
}
