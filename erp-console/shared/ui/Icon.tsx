// Material Symbols Outlined (font nạp ở app/layout.tsx), giống bản HTML cũ.
export function Icon({ name, className }: { name: string; className?: string }) {
  return (
    <i className={`mi${className ? ` ${className}` : ""}`} aria-hidden="true">
      {name}
    </i>
  );
}
