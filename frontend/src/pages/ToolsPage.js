import React, { useEffect, useState } from "react";
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

  // 載入所有筆記
  const loadNotes = async () => {
    const res = await fetch("/api/notes");
    const data = await res.json();
    setNotes(data);
  };

  useEffect(() => {
    loadNotes();
  }, []);

  // 編輯或新增
  const handleShowModal = (note) => {
    setCurrentNote(note || { id: "", title: "", code: "", purpose: "", result: "" });
    setShow(true);
  };

  // 刪除
  const handleDelete = async (id) => {
    if (window.confirm("確定要刪除此筆記嗎？")) {
      await fetch(`/api/notes/${id}`, { method: "DELETE" });
      loadNotes();
    }
  };

  // 提交表單
  const handleSave = async (e) => {
    e.preventDefault();
    const method = currentNote.id ? "PUT" : "POST";
    const url = currentNote.id ? `/api/notes/${currentNote.id}` : "/api/notes";
    await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentNote),
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
              <pre>
                <code>{n.code}</code>
              </pre>
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
              <Form.Label>程式碼</Form.Label>
              <Form.Control
                as="textarea"
                rows={4}
                value={currentNote.code}
                onChange={(e) => setCurrentNote({ ...currentNote, code: e.target.value })}
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
