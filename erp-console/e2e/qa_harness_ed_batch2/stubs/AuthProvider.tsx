// Giả AuthProvider cho khung thử: DetailPage/AiBlockFrame gọi useAuth() để biết có hiện giao diện AI hay không (W39).
export function useAuth() {
  return { me: { ai_features_enabled: true } };
}
