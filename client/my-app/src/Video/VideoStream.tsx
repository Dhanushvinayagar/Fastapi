// import { useEffect, useRef } from "react";

const VideoStream = () => {
    const videoUrl = "http://localhost:8000/video";

    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: '50px' }}>
        <h2>Custom Video Stream Player</h2>
        
        <video 
          controls 
          muted 
          autoPlay
          width="800" 
          height="450"
          style={{ borderRadius: '8px', boxShadow: '0 4px 8px rgba(0,0,0,0.2)' }}
        >
          <source src={videoUrl} type="video/mp4" />
          Your browser does not support the video tag.
        </video>
  
        <div style={{ marginTop: '20px', color: '#666' }}>
          <p>Streaming chunks dynamically from FastAPI backend...</p>
        </div>
      </div>
    );
}
    

export default VideoStream