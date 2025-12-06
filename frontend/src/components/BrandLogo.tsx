// src/components/BrandLogo.tsx
import { Link } from "react-router-dom";

// Use Vite's BASE_URL so it works under /TripleThreatx2/ on GitHub Pages
const logoUrl = `${import.meta.env.BASE_URL}triplethreat-logo.svg`;

type Props = {
  size?: number;        // pixel height of the logo mark
  withText?: boolean;   // whether to show the wordmark
  className?: string;
};

export default function BrandLogo({ size = 28, withText = false, className = "" }: Props) {
  return (
    <Link to="/" className={`inline-flex items-center gap-2 ${className}`} aria-label="TripleThreat Home">
      <img
        src={logoUrl}
        alt="TripleThreat"
        width={size}
        height={size}
        className="block"
        style={{ height: size, width: "auto" }}
      />
      {withText && <span className="text-base font-semibold tracking-tight">TripleThreat</span>}
    </Link>
  );
}
