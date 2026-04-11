import { TELEGRAM_BOT_HANDLE, TELEGRAM_BOT_URL } from "@/config/telegram";

export default function TelegramSessionHint() {
  return (
    <p className="text-muted-foreground text-center max-w-md">
      Open Learnix from the link in Telegram (menu <strong>Web app</strong> or{" "}
      <code className="text-xs">/web</code>) so your session is created. If you don&apos;t have an
      account yet, start{" "}
      <a
        href={TELEGRAM_BOT_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="text-primary font-medium underline underline-offset-2"
      >
        @{TELEGRAM_BOT_HANDLE}
      </a>{" "}
      and use <code className="text-xs">/start</code>.
    </p>
  );
}
