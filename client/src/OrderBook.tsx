import React, { useState, useEffect } from 'react';

const OrderBook = (props) => {
  const {clientId, symbol} = props;
  const [orders, setOrders] = useState({bids: [], asks:[]});
  const [error, setError] = useState();
//   const currencyPair = 'btcusdt';

//   const currencyArray = ['BTC', 'USDT'];

  useEffect(() => {
      if (clientId) {
        const ws = new WebSocket(`ws://localhost:8989/ws/${clientId}`);
        console.log(ws)
        ws.onopen = () => {
            ws.send(JSON.stringify(symbol));
        };
        ws.onmessage = (msg) => {
            const data = JSON.parse(msg.data);
            console.log(data)
            if (Object.keys(data).includes('error')) {

                setError(data.error);
                 ws.close();
            } else if (!!data._bids && !!data._asks) {
                return
             } else {
                setOrders({'bids': JSON.parse(data).bids, 'asks': JSON.parse(data).asks});
                console.log(orders)
            }
        };
        ws.onclose = () => {
          ws.close();
        };

        return () => {
          ws.close();
        };
      }

  }, [clientId, symbol]);

//   const { bids, asks } = orders;

  const orderRows = (arr) => {
  console.log(arr)
  return  arr.map((item, index) => (
      <tr key={index}>
        <td> {item[1]} </td>
        <td> {item[0]} </td>
      </tr>
    ));
  }

  const orderHead = (title) => {
        return (
        <thead>
          <tr>
            <th col-span="2">{title}</th>
          </tr>
        </thead>
      );
//       return (
//         <thead>
//           <tr>
//             <th col-span="2">{title}</th>
//           </tr>
//           <tr>
//             <th>Amount ({currencyArray[0]})</th>
//             <th>Price ({currencyArray[1]})</th>
//           </tr>
//         </thead>
//       );
  }

  return error ? (<div className="error"><b>{error}</b></div>):(
    <div className="order-container">
      <table>
        {orderHead('Bids')}
        <tbody>{orderRows(orders?.bids)}</tbody>
      </table>

      <table>
        {orderHead('Asks')}
        <tbody>{orderRows(orders?.asks)}</tbody>
      </table>
    </div>
  );
};

export default OrderBook;
