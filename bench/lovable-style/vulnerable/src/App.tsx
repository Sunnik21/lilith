import { BrowserRouter, Routes, Route } from "react-router-dom";
import Login from "./pages/Login";
import Upgrade from "./pages/Upgrade";
import Admin from "./pages/Admin";
import Post from "./pages/Post";
import Footer from "./components/Footer";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/upgrade" element={<Upgrade />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="/posts/:id" element={<Post />} />
      </Routes>
      <Footer />
    </BrowserRouter>
  );
}
