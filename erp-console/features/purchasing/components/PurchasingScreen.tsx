"use client";

import React from "react";
import { ReceiveBatchesForm } from "./ReceiveBatchesForm";
import s from "../purchasing.module.css";

export function PurchasingScreen() {
  return (
    <div className={s.screen}>
      <header className={s.header}>
        <h1 className={s.title}>Nhập lô mua tại cảng</h1>
        <p className={s.desc}>
          Ghi nhận phiếu nhập hàng kiểm đếm vật lý tại cảng. Mỗi dòng mặt hàng sinh MỘT lô cá riêng biệt (trạng thái Nháp — DRAFT).
        </p>
      </header>

      <ReceiveBatchesForm />
    </div>
  );
}
