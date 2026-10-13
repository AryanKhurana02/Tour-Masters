import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

interface DataHonestyCueProps {
  reviewedAt: string;
  dataMode: string;
}

export function DataHonestyCue({ reviewedAt, dataMode }: DataHonestyCueProps) {
  const location = useLocation();
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [lastUpdated, setLastUpdated] = useState("");

  useEffect(() => {
    setLastUpdated(new Date(reviewedAt).toLocaleTimeString());

    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [reviewedAt]);

  return (
    <div
      style={{
        padding: "12px",
        borderTop: `1px solid #d1d5db`,
        borderBottom: `1px solid #d1d5db`,
        background: "#f9fafb",
        marginTop: "12px",
        color: "#6b7280",
        fontSize: "0.85rem",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span>
          Data reviewed: {lastUpdated} · {dataMode.replace("_", " ")}
        </span>
        <span>{!isOnline && "🛰 Offline Mode"}</span>
      </div>
      <small>
        Estimates are rule-based, not live counts. Source: curated catalogue / reviewed_at.
      </small>
    </div>
  );
}