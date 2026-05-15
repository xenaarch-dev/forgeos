import type { Variants } from "framer-motion";

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.25 } },
  exit:   { opacity: 0, transition: { duration: 0.15 } },
};

export const fadeUp: Variants = {
  hidden:  { opacity: 0, y: 12 },
  visible: {
    opacity: 1, y: 0,
    transition: { duration: 0.4, ease: [0.25, 0.1, 0.25, 1] },
  },
  exit: { opacity: 0, y: -8, transition: { duration: 0.2 } },
};

export const staggerContainer: Variants = {
  hidden:  {},
  visible: { transition: { staggerChildren: 0.08 } },
};

export const staggerItem: Variants = {
  hidden:  { opacity: 0, y: 8, scale: 0.97 },
  visible: {
    opacity: 1, y: 0, scale: 1,
    transition: { duration: 0.3, ease: [0.25, 0.1, 0.25, 1] },
  },
};

export const slideInLeft: Variants = {
  hidden:  { opacity: 0, x: -16 },
  visible: {
    opacity: 1, x: 0,
    transition: { type: "spring", stiffness: 300, damping: 30 },
  },
  exit: { opacity: 0, x: -12, transition: { duration: 0.18 } },
};

export const sidebarVariants: Variants = {
  expanded:  { width: 280, transition: { type: "spring", stiffness: 260, damping: 28 } },
  collapsed: { width: 60,  transition: { type: "spring", stiffness: 260, damping: 28 } },
};

export const sidebarContentVariants: Variants = {
  expanded:  { opacity: 1, x: 0,   transition: { delay: 0.08, duration: 0.2 } },
  collapsed: { opacity: 0, x: -10, transition: { duration: 0.15 } },
};

export const logLineVariants: Variants = {
  hidden:  { opacity: 0, x: -4 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.15 } },
};

export const pulseRing: Variants = {
  hidden:  { opacity: 0, scale: 0.8 },
  visible: {
    opacity: [0.6, 0],
    scale: [1, 1.8],
    transition: { duration: 2, repeat: Infinity, ease: "easeOut" },
  },
};
