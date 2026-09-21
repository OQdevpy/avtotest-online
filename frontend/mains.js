var isDevToolsOpen = false;

function detectDevTools() {
    const element = new Image();
    Object.defineProperty(element, 'id', {
        get: function () {
            isDevToolsOpen = true;
            alert('Developer Tools detected');
        }
    });
    
    console.log(element);
    
    if (isDevToolsOpen) {
        console.clear(); // Console-ni tozalaydi
    }
}

// Har 5 sekundda tekshiradi
setInterval(detectDevTools, 5000);
