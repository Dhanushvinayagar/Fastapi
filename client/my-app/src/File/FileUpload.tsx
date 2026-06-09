import React from 'react'

const FileUpload = () => {

    const handleFileUpload = async (
        e: React.ChangeEvent<HTMLInputElement>
      ) => {
        const files = e.target.files;
      
        if (!files || files.length === 0) return;
      
        const formData = new FormData();
        formData.append("file", files[0]);
      
        const response = await fetch("http://127.0.0.1:8000/upload", {
          method: "POST",
          body: formData,
        });
      
        const data = await response.json();
        console.log(data);
      };
    
      
      // chunk 100kb at a time
      const CHUNK_SIZE = 1024 * 100;
      
      const uploadFileInChunks = async (e: React.ChangeEvent<HTMLInputElement>) => {
    
        if (!e.target.files || e.target.files.length === 0) return;
        const file: File = e.target.files?.[0];
    
        const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
    
        for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
          const start = chunkIndex * CHUNK_SIZE;
          const end = Math.min(start + CHUNK_SIZE, file.size);
    
          const chunk = file.slice(start, end);
    
          const formData = new FormData();
          formData.append("chunk", chunk);
          formData.append("filename", file.name);
          formData.append("chunkIndex", String(chunkIndex));
          formData.append("totalChunks", String(totalChunks));
    
          await fetch("http://127.0.0.1:8000/upload-chunk", {
            method: "POST",
            body: formData,
          });
        }
    
        console.log("Upload completed");
      };
    
      return (
        <>
          <div>
              File Upload 
              <input type="file" onChange={(e) => handleFileUpload(e)} />
          </div>
          <div>
            File Upload in chunks
            <input type="file" onChange={(e) => uploadFileInChunks(e)} />
          </div>
        </>
      )
}

export default FileUpload