"use client";

import { motion, useReducedMotion } from "framer-motion";

export function Reveal({
  children,
  delay = 0,
  className = "",
  y = 18,
  inView = true,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
  y?: number;
  inView?: boolean;
}) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  const anim = { opacity: 1, y: 0 };
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y }}
      {...(inView
        ? { whileInView: anim, viewport: { once: true, margin: "-60px" } }
        : { animate: anim })}
      transition={{ duration: 0.65, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
