import dynamic from "next/dynamic";

const Harness = dynamic(() => import("../../spikes/dw02/Harness"), {
  ssr: false,
});

export default function AiSpikePage() {
  const isEnabled = process.env.NEXT_PUBLIC_AI_SPIKE === "1";

  if (!isEnabled) {
    return (
      <div style={{ padding: 40, fontFamily: "sans-serif", textAlign: "center" }}>
        <h2>Không có trang này</h2>
        <p style={{ color: "#666" }}>
          Trang thử nghiệm AI spike chỉ khả dụng khi build với NEXT_PUBLIC_AI_SPIKE=1.
        </p>
      </div>
    );
  }

  return <Harness />;
}
