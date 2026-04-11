export class ClockController {
    constructor(options = {}) {
        this.clockElement = options.clockElement;
        this.containerElement = options.containerElement || document.body;
        this.pageId = options.pageId || 'default';
        
        console.log('[ClockController] Initializing for page:', this.pageId);
        console.log('[ClockController] Clock element:', this.clockElement);
        
        if (!this.clockElement) {
            console.error('[ClockController] Clock element is null or undefined');
            return;
        }
        
        this.clockTimeElement = this.clockElement.querySelector('.clock-time') || this.clockElement;
        console.log('[ClockController] Clock time element:', this.clockTimeElement);
        
        this.minSize = 2;
        this.maxSize = 20;
        this.sizeStep = 1;
        this.defaultSize = 9;
        
        this.state = {
            size: this.defaultSize,
            x: null,
            y: null,
            visible: true
        };
        
        this.isDragging = false;
        this.dragOffset = { x: 0, y: 0 };
        this.lastSavedWindowBounds = null;
        
        this.init();
    }
    
    async init() {
        console.log('[ClockController] init() called');
        this.setupElectronEvents();
        await this.loadState();
        console.log('[ClockController] Loaded state:', this.state);
        this.applyState();
        this.setupDrag();
        this.createControls();
        
        console.log('[ClockController] Initialization complete');
    }
    
    setupElectronEvents() {
        if (!window.electronAPI || !window.electronAPI.isElectron) {
            console.log('[ClockController] Not running in Electron, skipping Electron events');
            return;
        }
        
        console.log('[ClockController] Setting up Electron events');
        
        window.electronAPI.onRequestClockState(() => {
            console.log('[ClockController] Received request-clock-state');
            this.respondWithClockState();
        });
        
        window.electronAPI.onWindowResized(() => {
            console.log('[ClockController] Window resized');
            this.ensureClockInBounds();
        });
        
        window.electronAPI.onWindowMoved(() => {
            console.log('[ClockController] Window moved');
            this.ensureClockInBounds();
        });
        
        window.electronAPI.onWindowMaximized(() => {
            console.log('[ClockController] Window maximized');
            this.ensureClockInBounds();
        });
        
        window.electronAPI.onWindowUnmaximized(() => {
            console.log('[ClockController] Window unmaximized');
            this.ensureClockInBounds();
        });
    }
    
    async loadState() {
        if (window.electronAPI && window.electronAPI.isElectron) {
            try {
                const latestState = await window.electronAPI.getLatestState();
                console.log('[ClockController] Got latest state from Electron:', latestState);
                
                if (latestState && latestState.clock) {
                    const savedVisible = latestState.clock.visible;
                    this.state = { ...this.state, ...latestState.clock };
                    this.state.visible = savedVisible !== undefined ? savedVisible : true;
                    console.log('[ClockController] Applied Electron state:', this.state);
                    return;
                }
            } catch (e) {
                console.warn('[ClockController] Failed to load state from Electron:', e);
            }
        }
        
        const storageKey = `clockState_${this.pageId}`;
        const saved = localStorage.getItem(storageKey);
        
        console.log('[ClockController] Loading state from localStorage:', storageKey, saved);
        
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                const savedVisible = parsed.visible;
                this.state = { ...this.state, ...parsed };
                this.state.visible = savedVisible !== undefined ? savedVisible : true;
                console.log('[ClockController] Parsed state:', this.state);
            } catch (e) {
                console.warn('[ClockController] Failed to load clock state:', e);
            }
        }
    }
    
    saveState() {
        const storageKey = `clockState_${this.pageId}`;
        localStorage.setItem(storageKey, JSON.stringify(this.state));
    }
    
    respondWithClockState() {
        if (!window.electronAPI || !window.electronAPI.isElectron) return;
        
        const clockState = {
            size: this.state.size,
            x: this.state.x,
            y: this.state.y,
            visible: this.state.visible
        };
        
        console.log('[ClockController] Sending clock state to main process:', clockState);
        window.electronAPI.saveState(clockState);
    }
    
    async ensureClockInBounds() {
        if (!this.clockElement || !this.state.visible) return;
        
        try {
            const bounds = await window.electronAPI.getWindowBounds();
            if (!bounds) return;
            
            const containerWidth = bounds.width;
            const containerHeight = bounds.height;
            
            const clockRect = this.clockElement.getBoundingClientRect();
            const clockWidth = clockRect.width;
            const clockHeight = clockRect.height;
            
            let needsUpdate = false;
            let newX = this.state.x;
            let newY = this.state.y;
            
            if (this.state.x === null || this.state.y === null) {
                return;
            }
            
            const maxX = containerWidth - clockWidth;
            const maxY = containerHeight - clockHeight;
            
            if (this.state.x > maxX) {
                newX = Math.max(0, maxX);
                needsUpdate = true;
            } else if (this.state.x < 0) {
                newX = 0;
                needsUpdate = true;
            }
            
            if (this.state.y > maxY) {
                newY = Math.max(0, maxY);
                needsUpdate = true;
            } else if (this.state.y < 0) {
                newY = 0;
                needsUpdate = true;
            }
            
            if (needsUpdate) {
                console.log('[ClockController] Adjusting clock position to stay in bounds');
                this.state.x = newX;
                this.state.y = newY;
                this.applyState();
                this.saveState();
            }
        } catch (e) {
            console.warn('[ClockController] Failed to ensure clock in bounds:', e);
        }
    }
    
    applyState() {
        if (!this.clockElement) return;
        
        console.log('[ClockController] Applying state:', this.state);
        
        if (this.clockTimeElement) {
            this.clockTimeElement.style.fontSize = `${this.state.size}rem`;
        }
        
        if (this.state.x !== null && this.state.y !== null) {
            this.clockElement.style.right = 'auto';
            this.clockElement.style.bottom = 'auto';
            this.clockElement.style.left = `${this.state.x}px`;
            this.clockElement.style.top = `${this.state.y}px`;
        }
        
        if (this.state.visible) {
            this.clockElement.classList.remove('hidden');
            console.log('[ClockController] Clock set to visible');
        } else {
            this.clockElement.classList.add('hidden');
            console.log('[ClockController] Clock set to hidden');
        }
    }
    
    setupDrag() {
        if (!this.clockElement) return;
        
        this.clockElement.style.cursor = 'move';
        this.clockElement.style.pointerEvents = 'auto';
        this.clockElement.style.userSelect = 'none';
        
        this.clockElement.addEventListener('mousedown', (e) => this.startDrag(e));
        this.clockElement.addEventListener('touchstart', (e) => this.startDrag(e), { passive: false });
        
        if (this.clockTimeElement && this.clockTimeElement !== this.clockElement) {
            this.clockTimeElement.style.pointerEvents = 'auto';
            this.clockTimeElement.style.cursor = 'move';
            this.clockTimeElement.style.userSelect = 'none';
            this.clockTimeElement.addEventListener('mousedown', (e) => this.startDrag(e));
            this.clockTimeElement.addEventListener('touchstart', (e) => this.startDrag(e), { passive: false });
            this.clockTimeElement.addEventListener('wheel', (e) => this.handleWheel(e), { passive: false });
        }
        
        document.addEventListener('mousemove', (e) => this.drag(e));
        document.addEventListener('touchmove', (e) => this.drag(e), { passive: false });
        
        document.addEventListener('mouseup', () => this.endDrag());
        document.addEventListener('touchend', () => this.endDrag());
        
        this.clockElement.addEventListener('wheel', (e) => this.handleWheel(e), { passive: false });
    }
    
    handleWheel(e) {
        if (!this.state.visible) return;
        
        e.preventDefault();
        e.stopPropagation();
        
        if (e.deltaY < 0) {
            this.increaseSize();
        } else {
            this.decreaseSize();
        }
        
        return false;
    }
    
    startDrag(e) {
        if (!this.state.visible) return;
        
        e.preventDefault();
        e.stopPropagation();
        this.isDragging = true;
        
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        
        const rect = this.clockElement.getBoundingClientRect();
        this.dragOffset.x = clientX - rect.left;
        this.dragOffset.y = clientY - rect.top;
        
        this.clockElement.style.transition = 'none';
    }
    
    drag(e) {
        if (!this.isDragging) return;
        
        e.preventDefault();
        
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        
        let newX = clientX - this.dragOffset.x;
        let newY = clientY - this.dragOffset.y;
        
        const containerRect = this.containerElement.getBoundingClientRect();
        const clockRect = this.clockElement.getBoundingClientRect();
        
        const maxX = containerRect.width - clockRect.width;
        const maxY = containerRect.height - clockRect.height;
        
        newX = Math.max(0, Math.min(newX, maxX));
        newY = Math.max(0, Math.min(newY, maxY));
        
        this.clockElement.style.right = 'auto';
        this.clockElement.style.bottom = 'auto';
        this.clockElement.style.left = `${newX}px`;
        this.clockElement.style.top = `${newY}px`;
        
        this.state.x = newX;
        this.state.y = newY;
    }
    
    endDrag() {
        if (!this.isDragging) return;
        
        this.isDragging = false;
        this.clockElement.style.transition = '';
        this.saveState();
        this.updateControlsPosition();
    }
    
    createControls() {
        const controlsContainer = document.createElement('div');
        controlsContainer.className = 'clock-controls';
        controlsContainer.innerHTML = `
            <span class="clock-hint">滚轮调节大小</span>
            <button class="clock-ctrl-btn reset-position" title="重置位置和大小">
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/>
                </svg>
            </button>
        `;
        
        this.clockElement.parentNode.appendChild(controlsContainer);
        
        controlsContainer.querySelector('.reset-position').addEventListener('click', (e) => {
            e.stopPropagation();
            this.resetPosition();
        });
        
        this.controlsContainer = controlsContainer;
        this.updateControlsPosition();
    }
    
    updateControlsPosition() {
        if (!this.controlsContainer || !this.clockElement) return;
        
        const clockRect = this.clockElement.getBoundingClientRect();
        const containerRect = this.containerElement.getBoundingClientRect();
        
        this.controlsContainer.style.position = 'absolute';
        this.controlsContainer.style.left = `${this.state.x !== null ? this.state.x : containerRect.width - clockRect.width - 48}px`;
        this.controlsContainer.style.top = `${this.state.y !== null ? this.state.y + clockRect.height + 8 : ''}`;
        this.controlsContainer.style.bottom = this.state.y === null ? `${containerRect.height - (this.state.y || 0)}px` : '';
        this.controlsContainer.style.right = this.state.x === null ? '3rem' : '';
    }
    
    increaseSize() {
        if (this.state.size < this.maxSize) {
            this.state.size = Math.min(this.state.size + this.sizeStep, this.maxSize);
            this.applyState();
            this.saveState();
        }
    }
    
    decreaseSize() {
        if (this.state.size > this.minSize) {
            this.state.size = Math.max(this.state.size - this.sizeStep, this.minSize);
            this.applyState();
            this.saveState();
        }
    }
    
    resetPosition() {
        this.state.x = null;
        this.state.y = null;
        this.state.size = this.defaultSize;
        
        this.clockElement.style.left = '';
        this.clockElement.style.top = '';
        this.clockElement.style.right = '';
        this.clockElement.style.bottom = '';
        
        this.applyState();
        this.saveState();
    }
    
    toggle() {
        this.state.visible = !this.state.visible;
        this.applyState();
        this.saveState();
        return this.state.visible;
    }
}

export function saveWindowState(pageId) {
    console.log('[ClockController] saveWindowState is deprecated, state is now saved automatically');
}

export function loadWindowState(pageId) {
    console.log('[ClockController] loadWindowState is deprecated, state is now loaded from Electron');
    return null;
}

export function injectClockStyles() {
    if (document.getElementById('clock-controller-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'clock-controller-styles';
    style.textContent = `
        .clock-controls {
            position: absolute;
            display: flex;
            gap: 4px;
            z-index: 25;
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
            align-items: center;
        }
        
        .clock-overlay:hover ~ .clock-controls,
        .clock-controls:hover,
        .clock-overlay.dragging ~ .clock-controls {
            opacity: 1;
            pointer-events: auto;
        }
        
        .clock-ctrl-btn {
            width: 32px;
            height: 32px;
            border: none;
            border-radius: 4px;
            background: rgba(0, 0, 0, 0.6);
            color: rgba(255, 255, 255, 0.8);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            backdrop-filter: blur(4px);
        }
        
        .clock-ctrl-btn:hover {
            background: rgba(229, 9, 20, 0.8);
            color: #fff;
            transform: scale(1.1);
        }
        
        .clock-ctrl-btn:active {
            transform: scale(0.95);
        }
        
        .clock-ctrl-btn svg {
            width: 18px;
            height: 18px;
        }
        
        .clock-hint {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.6);
            padding: 4px 8px;
            background: rgba(0, 0, 0, 0.4);
            border-radius: 4px;
            white-space: nowrap;
        }
        
        .clock-overlay {
            pointer-events: auto;
            cursor: move;
            user-select: none;
            transition: opacity 0.3s ease, transform 0.1s ease;
        }
        
        .clock-overlay.dragging {
            opacity: 0.8;
        }
        
        @media (max-width: 768px) {
            .clock-ctrl-btn {
                width: 28px;
                height: 28px;
            }
            
            .clock-ctrl-btn svg {
                width: 16px;
                height: 16px;
            }
            
            .clock-hint {
                font-size: 10px;
            }
        }
    `;
    document.head.appendChild(style);
}
