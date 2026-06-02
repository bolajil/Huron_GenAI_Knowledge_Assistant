import React, { ReactNode, useState, useMemo, MouseEvent, CSSProperties } from 'react';

interface RippleState {
  key: number;
  x: number;
  y: number;
  size: number;
  color: string;
}

interface RippleButtonProps {
  children: ReactNode;
  onClick?: (event: MouseEvent<HTMLButtonElement>) => void;
  className?: string;
  disabled?: boolean;
  variant?: 'default' | 'hover' | 'ghost' | 'hoverborder';
  rippleColor?: string;
  rippleDuration?: number;
  hoverBaseColor?: string;
  hoverRippleColor?: string;
  hoverBorderEffectColor?: string;
  hoverBorderEffectThickness?: string;
}

const hexToRgba = (hex: string, alpha: number): string => {
  let hexValue = hex.startsWith('#') ? hex.slice(1) : hex;
  if (hexValue.length === 3) hexValue = hexValue.split('').map(c => c + c).join('');
  const r = parseInt(hexValue.slice(0, 2), 16);
  const g = parseInt(hexValue.slice(2, 4), 16);
  const b = parseInt(hexValue.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

const GRID_HOVER_NUM_COLS = 36;
const GRID_HOVER_NUM_ROWS = 12;
const GRID_HOVER_TOTAL_CELLS = GRID_HOVER_NUM_COLS * GRID_HOVER_NUM_ROWS;
const GRID_HOVER_RIPPLE_EFFECT_SIZE = "18.973665961em";

const JS_RIPPLE_KEYFRAMES = `
  @keyframes js-ripple-animation {
    0% { transform: scale(0); opacity: 1; }
    100% { transform: scale(1); opacity: 0; }
  }
  .animate-js-ripple-effect {
    animation: js-ripple-animation var(--ripple-duration) ease-out forwards;
  }
`;

const RippleButton: React.FC<RippleButtonProps> = ({
  children, onClick, className = '', disabled = false, variant = 'default',
  rippleColor: userProvidedRippleColor, rippleDuration = 600,
  hoverBaseColor = '#6996e2', hoverRippleColor: customHoverRippleColor,
  hoverBorderEffectColor = '#6996e277', hoverBorderEffectThickness = '0.3em',
}) => {
  const [jsRipples, setJsRipples] = useState<RippleState[]>([]);

  const determinedJsRippleColor = useMemo(() => {
    if (userProvidedRippleColor) return userProvidedRippleColor;
    return 'var(--button-ripple-color, rgba(0, 0, 0, 0.1))';
  }, [userProvidedRippleColor]);

  const dynamicGridHoverStyles = useMemo(() => {
    let rules = '';
    const cellDim = 0.25;
    const duration = '0.9s';
    for (let r = 0; r < GRID_HOVER_NUM_ROWS; r++) {
      for (let c = 0; c < GRID_HOVER_NUM_COLS; c++) {
        const idx = r * GRID_HOVER_NUM_COLS + c + 1;
        const top = 0.125 + r * cellDim;
        const left = 0.1875 + c * cellDim;
        if (variant === 'hover') {
          rules += `.hover-variant-grid-cell:nth-child(${idx}):hover ~ .hover-variant-visual-ripple { top: ${top}em; left: ${left}em; transition: width ${duration} ease, height ${duration} ease, top 0s linear, left 0s linear; }`;
        } else if (variant === 'hoverborder') {
          rules += `.hoverborder-variant-grid-cell:nth-child(${idx}):hover ~ .hoverborder-variant-visual-ripple { top: ${top}em; left: ${left}em; transition: width ${duration} ease-out, height ${duration} ease-out, top 0s linear, left 0s linear; }`;
        }
      }
    }
    if (variant === 'hover') {
      const color = customHoverRippleColor ?? hexToRgba(hoverBaseColor, 0.466);
      return `.hover-variant-visual-ripple { background-color: ${color}; transition: width ${duration} ease, height ${duration} ease, top 99999s linear, left 99999s linear; } .hover-variant-grid-cell:hover ~ .hover-variant-visual-ripple { width: ${GRID_HOVER_RIPPLE_EFFECT_SIZE}; height: ${GRID_HOVER_RIPPLE_EFFECT_SIZE}; } ${rules}`;
    }
    if (variant === 'hoverborder') {
      return `.hoverborder-variant-ripple-container { padding: ${hoverBorderEffectThickness}; mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0); mask-composite: exclude; -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0); -webkit-mask-composite: xor; } .hoverborder-variant-visual-ripple { background-color: ${hoverBorderEffectColor}; transition: width ${duration} ease-out, height ${duration} ease-out, top 99999s linear, left 9999s linear; } .hoverborder-variant-grid-cell:hover ~ .hoverborder-variant-visual-ripple { width: ${GRID_HOVER_RIPPLE_EFFECT_SIZE}; height: ${GRID_HOVER_RIPPLE_EFFECT_SIZE}; } ${rules}`;
    }
    return '';
  }, [variant, hoverBaseColor, customHoverRippleColor, hoverBorderEffectColor, hoverBorderEffectThickness]);

  const createJsRipple = (event: MouseEvent<HTMLButtonElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 2;
    const ripple: RippleState = { key: Date.now(), x: event.clientX - rect.left - size / 2, y: event.clientY - rect.top - size / 2, size, color: determinedJsRippleColor };
    setJsRipples(prev => [...prev, ripple]);
    setTimeout(() => setJsRipples(cur => cur.filter(r => r.key !== ripple.key)), rippleDuration);
  };

  const handleClick = (e: MouseEvent<HTMLButtonElement>) => {
    if (!disabled) { createJsRipple(e); onClick?.(e); }
  };

  const rippleEls = (
    <div className="absolute inset-0 pointer-events-none z-[5]">
      {jsRipples.map(r => (
        <span key={r.key} className="absolute rounded-full animate-js-ripple-effect"
          style={{ left: r.x, top: r.y, width: r.size, height: r.size, backgroundColor: r.color, ['--ripple-duration' as string]: `${rippleDuration}ms` } as CSSProperties} />
      ))}
    </div>
  );

  if (variant === 'ghost') {
    return (
      <>
        <style dangerouslySetInnerHTML={{ __html: JS_RIPPLE_KEYFRAMES }} />
        <button className={`relative border-none bg-transparent isolate overflow-hidden cursor-pointer px-4 py-2 rounded-lg text-lg ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`} onClick={handleClick} disabled={disabled}>
          <span className="relative z-10 pointer-events-none">{children}</span>
          {rippleEls}
        </button>
      </>
    );
  }

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: JS_RIPPLE_KEYFRAMES }} />
      {(variant === 'hover' || variant === 'hoverborder') && <style dangerouslySetInnerHTML={{ __html: dynamicGridHoverStyles }} />}
      <button className={`relative border-none overflow-hidden isolate transition-all duration-200 cursor-pointer px-4 py-2 bg-blue-600 hover:opacity-90 text-white rounded-lg ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`} onClick={handleClick} disabled={disabled}>
        <span className="relative z-[1] pointer-events-none">{children}</span>
        {rippleEls}
      </button>
    </>
  );
};

export { RippleButton };
