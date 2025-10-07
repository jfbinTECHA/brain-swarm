import "@/styles/globals.css";
import type { AppProps } from "next/app";

export default function MyApp({ Component, pageProps }: AppProps) {
  return (
    <div className="bg-graphite text-gray-100 min-h-screen">
      <Component {...pageProps} />
    </div>
  );
}