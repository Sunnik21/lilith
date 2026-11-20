import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

type Order = { id: string; user_id: string; total: number; email: string };

export default function Admin() {
  const [orders, setOrders] = useState<Order[]>([]);

  useEffect(() => {
    supabase.from("orders").select("*").then(({ data }) => setOrders(data ?? []));
  }, []);

  return (
    <table>
      <tbody>
        {orders.map((o) => (
          <tr key={o.id}><td>{o.email}</td><td>{o.total}</td></tr>
        ))}
      </tbody>
    </table>
  );
}
