import { useState, useEffect} from "react";

function App(){
  const [companies, setComapnies]=useState([]);

  useEffect(() =>{ 
  fetch("http://127.0.0.1:8000/companies/score")
  .then((res) => res.json())
  .then((data)=>setComapnies(data));

},[]);

return(
  <div>
    <h1> FinSight Ai</h1>
    <ul>
      {companies.map((c)=>(
        <li key ={c.ticker}>
          {c.ticker}-{c.score}-{c.label}
        </li>
      ))}
    </ul>
  </div>
);



}
export default App;