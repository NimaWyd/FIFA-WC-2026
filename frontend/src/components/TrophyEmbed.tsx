"use client";

const SKETCHFAB_SRC =
  "https://sketchfab.com/models/76fe488adc344a4bbd2e18698f551bd6/embed?autostart=1&ui_theme=dark&ui_infos=0&ui_controls=0&ui_watermark=0&transparent=1";

export default function TrophyEmbed({ className }: { className?: string }) {
  return (
    <div className={className}>
      <iframe
        title="FIFA World Cup Trophy"
        src={SKETCHFAB_SRC}
        allow="autoplay; fullscreen; xr-spatial-tracking"
        allowFullScreen
        style={{ width: "100%", height: "100%", border: "none", borderRadius: 12 }}
      />
    </div>
  );
}
