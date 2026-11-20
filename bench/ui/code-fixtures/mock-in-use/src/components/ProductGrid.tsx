import { mockProducts } from "../data/mockProducts";

export default function ProductGrid() {
  return (
    <ul>
      {mockProducts.map((p) => (
        <li key={p.id}>{p.name}: ${(p.price / 100).toFixed(2)}</li>
      ))}
    </ul>
  );
}
