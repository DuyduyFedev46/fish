/**
 * GUI-13: nhãn thời gian giao ở giỏ hàng. Câu chữ và các con số (2 giờ, 4 giờ, 15 km) nằm ở đây
 * để đổi một chỗ. Chỉ là chữ cố định: FE không đo khoảng cách, không đổi API.
 */
export const DELIVERY_ETA = {
  nearHours: 2,
  farHours: 4,
  radiusKm: 15,
} as const;

export const DELIVERY_ETA_TEXT =
  `Giao trong ${DELIVERY_ETA.nearHours} giờ kể từ lúc đặt hàng nếu cách vựa dưới ${DELIVERY_ETA.radiusKm} km` +
  ` · Từ ${DELIVERY_ETA.radiusKm} km trở lên: trong ${DELIVERY_ETA.farHours} giờ`;
