import { useState } from 'react';
import './App.css'
import FileUpload from './File/FileUpload'
import VideoStream from './Video/VideoStream';

const tabs = ['file','video']

function App() {
  const [tab, setTab] = useState(tabs[0]);

  return (
    <div className="App">
        <div className="tabs">
            <button onClick={(_)=>setTab(tabs[0])}>File</button>
            <button onClick={(_)=>setTab(tabs[1])}>Video</button>
        </div>
        {tab === 'file' && <FileUpload />}
        {tab === 'video' && <VideoStream />}
    </div>
  )
}

export default App
