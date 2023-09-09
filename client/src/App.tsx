import React from "react";
import OrderBook from "./OrderBook";
import { useState, useEffect } from 'react';
import { useDebouncedCallback } from 'use-debounce';

const App = () => {
    const [clientId, setClientId] = useState();
    const [symbol, setSymbol] = useState('')

    useEffect(() => {
        const url = 'http://localhost:8989/register';
        const getOrderPairs = async () => {
          const resp = await  fetch(url, {headers: {"Content-Type": "application/json"}, method: "POST"})
          const data = await resp.json()
          console.log(data)
          setClientId(data)
        };
        getOrderPairs()
    }, [])

  const debounced = useDebouncedCallback(
    // function
    (value) => {
      setSymbol(value);
    },
    // delay in ms
    1000
  );

  const handleFocus = (event) => {
    event.target.value = ''
                setSymbol('');
            };


  return (
    <div>
      <h2>Crypto Order Book </h2>
      <div className="symbol-input">
        <label htmlFor="name">Order book symbol. Eg: BTCUSDT</label>
        <input type="text" id="name" name="name" required minLength={4} onChange={e => debounced(e.target.value)} onFocus={e=>handleFocus(e)}/>
      </div>
       {!!symbol ? (<OrderBook clientId={clientId} symbol={symbol}/>) : (<div className="help-info">Pls provide market exchange symbol. </div>)}
    </div>
  );
};

export default App;
