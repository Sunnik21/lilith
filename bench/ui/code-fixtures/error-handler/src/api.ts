export async function loadInvoices(userId: string) {
  console.log("loading invoices for", userId);
  try {
    const res = await fetch(`/api/invoices?user=${userId}`);
    console.log("status", res.status);
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("Could not load invoices", err);
    throw err;
  }
}
