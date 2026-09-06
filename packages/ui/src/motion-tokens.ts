/** Presentation timing in seconds. No token controls application state. */
export const motionTokens = {
  ease: [0.2, 0.8, 0.2, 1] as const,
  press: { duration: 0.1, ease: [0.2, 0.8, 0.2, 1] as const },
  hover: { duration: 0.12, ease: [0.2, 0.8, 0.2, 1] as const },
  selection: { duration: 0.18, ease: [0.2, 0.8, 0.2, 1] as const },
  panel: { duration: 0.16, ease: [0.2, 0.8, 0.2, 1] as const },
  dialog: { duration: 0.18, ease: [0.2, 0.8, 0.2, 1] as const },
  spring: { type: 'spring' as const, stiffness: 400, damping: 40, mass: 0.8 },
};
