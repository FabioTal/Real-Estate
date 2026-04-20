const { app, BrowserWindow, shell } = require('electron')
const path = require('path')
const { spawn, exec } = require('child_process')

let mainWindow
let backendProcess

const isDev = process.env.NODE_ENV === 'development'

function getResourcePath(...parts) {
  if (isDev) {
    return path.join(__dirname, '..', ...parts)
  }
  return path.join(process.resourcesPath, ...parts)
}

function openInWindowsBrowser(url) {
  exec(`cmd.exe /c start "" "${url}"`, (err) => {
    if (err) {
      exec(`powershell.exe Start-Process "${url}"`, (err2) => {
        if (err2) console.error('Could not open browser:', err2)
      })
    }
  })
}

function startBackend() {
  const pythonPath = path.join(getResourcePath('venv'), 'bin', 'python3')
  const backendPath = path.join(getResourcePath('backend'), 'main.py')

  console.log('Starting backend:', pythonPath, backendPath)

  backendProcess = spawn(pythonPath, [backendPath], {
    cwd: getResourcePath(),
    env: { ...process.env }
  })

  backendProcess.stdout.on('data', (data) => {
    console.log(`Backend: ${data}`)
  })

  backendProcess.stderr.on('data', (data) => {
    console.error(`Backend error: ${data}`)
  })

  backendProcess.on('close', (code) => {
    console.log(`Backend exited with code ${code}`)
  })
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
    backgroundColor: '#0f0f0f',
    show: false,
    title: 'Property AI Agent Albania',
  })

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'))
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    openInWindowsBrowser(url)
    return { action: 'deny' }
  })

  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (url !== 'http://localhost:5173' && !url.startsWith('file://')) {
      event.preventDefault()
      openInWindowsBrowser(url)
    }
  })

  mainWindow.on('close', (event) => {
    if (!app.isQuiting) {
      event.preventDefault()
      mainWindow.hide()
    }
  })
}

app.whenReady().then(() => {
  startBackend()
  setTimeout(() => {
    createWindow()
  }, 2000)
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    if (backendProcess) backendProcess.kill()
    app.quit()
  }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})
