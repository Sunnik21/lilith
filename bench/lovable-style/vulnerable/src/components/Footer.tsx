import { useEffect, useRef } from "react";

export default function Footer() {
  const iconRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (iconRef.current) {
      iconRef.current.innerHTML = '<svg width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="6" r="5"/></svg>';
    }
  }, []);

  return (
    <footer>
      <span ref={iconRef} /> NoteNest
    </footer>
  );
}
