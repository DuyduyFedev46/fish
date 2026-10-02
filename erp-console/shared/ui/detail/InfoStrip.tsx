// Dải tóm tắt trên đầu trang chi tiết (board D2b: "Đặt lúc | Còn giữ chỗ | Tự huỷ lúc"): một thẻ viền mỏng, các ô nằm ngang
// (nhãn nhỏ trên, giá trị dưới), ngăn bằng đường kẻ đứng, xuống dòng khi hẹp. Các ô là <InfoField>, nên vẫn là cặp dt/dd.
import s from "./InfoStrip.module.css";

export function InfoStrip({ children, label }: { children: React.ReactNode; label: string }) {
  return (
    <section className={s.strip} aria-label={label}>
      <dl className={s.list}>{children}</dl>
    </section>
  );
}
