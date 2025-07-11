// src/pages/NewsPage.js
import React, { useEffect, useState } from "react";

export default function NewsPage() {
  const [article, setArticle] = useState(null);

  useEffect(() => {
    fetch("/api/news")
      .then(res => res.json())
      .then(data => {
        console.log("NewsPage data:", data);
        if (Array.isArray(data.articles) && data.articles.length > 0) {
          setArticle(data.articles[0]);
        } else {
          setArticle(null);
        }
      })
      .catch(err => {
        console.error("取得新聞失敗:", err);
        setArticle(null);
      });
  }, []);

  if (!article) {
    return <p>目前沒有新聞。</p>;
  }

  return (
    <div>
      <h3>最新新聞</h3>
      <div className="card">
        {article.image && (
          <img src={article.image} className="card-img-top" alt="" />
        )}
        <div className="card-body">
          <h5 className="card-title">{article.title}</h5>
          <p className="card-text">
            <small className="text-muted">{article.source}</small>
          </p>
          <a href={article.url} className="btn btn-primary" target="_blank" rel="noreferrer">
            閱讀原文
          </a>
        </div>
      </div>
    </div>
  );
}
