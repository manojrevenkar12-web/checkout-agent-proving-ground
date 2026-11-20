/**
 * One orchestrated moment: on first load the receipt prints, line by line. After that, motion only answers an
 * action: a placed order's steps print as the agent took them.
 */
export const motion = { quick: 0.16, settle: 0.4, stagger: 0.05, ease: [0.2, 0.7, 0.2, 1] as const } as const;
