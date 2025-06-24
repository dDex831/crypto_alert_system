import React, { useEffect, useState } from "react";

export default function NewsPage() {
  const [news, setNews] = useState({ blockchain: [], economy: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchNews() {
      setLoading(true);
      try {
        const res = await fetch("/api/news");
        const data = await res.json();
        setNews(data);
      } catch (err) {
        setNews({ blockchain: [], economy: [] });
      }
      setLoading(false);
    }
    fetchNews();
  }, []);

  return (
    <section>
      <h3>每日新聞摘要</h3>
      {loading ? (
        <div>載入中...</div>
      ) : (
        <>
          <h5>🔗 區塊鏈熱門文章</h5>
          {news.blockchain.map((i, idx) => (
            <div className="mb-4" key={idx}>
              <p>{i.title}</p>
              {i.image && <img src={i.image} alt="" style={{ maxWidth: "100%", borderRadius: 8 }} />}
              <p>
                <a href={i.url} target="_blank" rel="noopener noreferrer">
                  閱讀原文
                </a>
              </p>
            </div>
          ))}
          <h5>💹 經濟熱門文章</h5>
          {news.economy.map((i, idx) => (
            <div className="mb-4" key={idx}>
              <p>{i.title}</p>
              {i.image && <img src={i.image} alt="" style={{ maxWidth: "100%", borderRadius: 8 }} />}
              <p>
                <a href={i.url} target="_blank" rel="noopener noreferrer">
                  閱讀原文
                </a>
              </p>
            </div>
          ))}
        </>
      )}
    </section>
  );
}
