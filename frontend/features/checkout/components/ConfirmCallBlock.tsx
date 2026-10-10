import Banner from "@/components/ui/Banner";

/**
 * Giờ gọi xác nhận (thay ConfirmCallNotice cũ có "đuôi SĐT" và câu "hoàn đủ tiền"). Chỉ có khung giờ, không số điện thoại khách
 * (trang đơn công khai không hiện người nhận). Khung giờ do chỗ gọi lấy từ site-info.
 */
export default function ConfirmCallBlock({ hours }: { hours: string }) {
  return (
    <Banner tone="info" icon="phone">
      Cá Về sẽ gọi số điện thoại đặt hàng trong khung {hours} để xác nhận trước khi giao.
    </Banner>
  );
}
