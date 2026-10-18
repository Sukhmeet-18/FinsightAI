import { useState, useEffect } from "react";

export default function Robo() {
  const [questions, setQuestions] = useState([]);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/robo/questions")
      .then((res) => res.json())
      .then((data) => setQuestions(data));
  }, []);

  return (
    <div>
      <h2>Risk Quiz</h2>
      {questions.map((q) => (
        <div key={q.id}>
          <p>{q.id}. {q.text}</p>
          {q.options.map((opt, i) => (
            <div key={i}>{i + 1}. {opt}</div>
          ))}
        </div>
      ))}
    </div>
  );
}