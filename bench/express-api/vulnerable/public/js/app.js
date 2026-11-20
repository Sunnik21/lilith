const button = document.querySelector("#search-btn");
const results = document.querySelector("#results");

button.addEventListener("click", async () => {
  results.innerHTML = '<span class="spinner" aria-label="Loading"></span>';
  const q = document.querySelector("#q").value;
  const res = await fetch(`/search?q=${encodeURIComponent(q)}`);
  const products = await res.json();
  results.replaceChildren(...products.map((p) => {
    const li = document.createElement("li");
    li.textContent = `${p.name}: $${(p.price / 100).toFixed(2)}`;
    return li;
  }));
});
