import streamlit as st
import os
import cv2
import tempfile
import zipfile
import time
from pathlib import Path

def extract_frames(video_path, fps):
    """Extract frames from video at specified FPS"""
    try:
        start_time = time.time()
        temp_dir = tempfile.mkdtemp(prefix="frames_")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return "Error: Could not open video file", None

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / video_fps

        st.info(f"Video FPS: {video_fps:.2f}, Duration: {duration:.2f}s")
        st.info(f"Total frames: {total_frames}")
        st.info(f"Target FPS: {fps}")
        
        # Robust extraction: read all available frames sequentially
        st.info("Using robust sequential extraction...")
        
        extracted_count = 0
        frame_idx = 0
        frames_read = 0
        
        # First pass: count actual readable frames
        with st.spinner("Counting actual readable frames..."):
            while True:
                ret, _ = cap.read()
                if not ret:
                    break
                frames_read += 1
        
        st.success(f"Actually readable frames: {frames_read}")
        actual_duration = frames_read / video_fps
        st.info(f"Actual video duration: {actual_duration:.2f}s")
        
        # Reset to beginning
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        # Calculate frame interval based on actual frames
        expected_output_frames = int(actual_duration * fps)
        frame_interval = max(1, int(round(frames_read / expected_output_frames))) if expected_output_frames > 0 else 1
        
        st.info(f"Expected output frames: {expected_output_frames}")
        st.info(f"Frame interval: {frame_interval}")
        
        # Second pass: extract frames
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Extract frame if it matches our interval
            if frame_idx % frame_interval == 0:
                frame_filename = f"frame_{extracted_count:06d}.jpg"
                frame_path = os.path.join(temp_dir, frame_filename)
                cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                extracted_count += 1
                
                # Update progress
                if expected_output_frames > 0:
                    progress = min(extracted_count / expected_output_frames, 1.0)
                    progress_bar.progress(progress)
                    status_text.text(f"Extracted {extracted_count} frames...")
            
            frame_idx += 1

        st.success(f"Sequential extraction completed. Extracted: {extracted_count} frames")

        cap.release()

        # Zip frames
        zip_path = os.path.join(temp_dir, "extracted_frames.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.jpg'):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)

        elapsed_time = time.time() - start_time
        actual_output_fps = extracted_count / actual_duration if actual_duration > 0 else 0

        success_message = f"""
        ✅ Frame extraction completed!

        📊 Stats:
        - Video FPS: {video_fps:.2f}
        - Target FPS: {fps:.2f}
        - Metadata duration: {duration:.2f}s
        - Actual duration: {actual_duration:.2f}s
        - Actual frames: {frames_read}
        - Expected output frames: {expected_output_frames}
        - Extracted frames: {extracted_count}
        - Actual output FPS: {actual_output_fps:.2f}
        - Processing time: {elapsed_time:.2f}s
        
        Note: Video metadata was incorrect - using actual readable frames.
        """
        
        return success_message, zip_path

    except Exception as e:
        return f"❌ Error: {str(e)}", None

# Streamlit app
st.set_page_config(
    page_title="Video Frame Extractor",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 Video Frame Extractor")
st.markdown("Upload a video and specify the desired FPS to extract frames.")

# Sidebar for inputs
with st.sidebar:
    st.header("📤 Input Parameters")
    
    uploaded_file = st.file_uploader(
        "Choose a video file",
        type=['mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv'],
        help="Supported formats: MP4, AVI, MOV, MKV, WMV, FLV"
    )
    
    fps_input = st.number_input(
        "Extraction FPS",
        min_value=0.1,
        max_value=60.0,
        value=1.0,
        step=0.1,
        help="Frames per second to extract from video"
    )
    
    process_button = st.button(
        "🚀 Extract Frames",
        type="primary",
        use_container_width=True
    )

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📊 Processing Results")
    
    if uploaded_file is not None:
        st.video(uploaded_file)
        
        if process_button:
            if uploaded_file is not None:
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                try:
                    # Process the video
                    message, zip_path = extract_frames(tmp_file_path, fps_input)
                    
                    # Display results
                    st.markdown(message)
                    
                    # Provide download link if successful
                    if zip_path and os.path.exists(zip_path):
                        with open(zip_path, 'rb') as f:
                            st.download_button(
                                label="📥 Download Extracted Frames (ZIP)",
                                data=f.read(),
                                file_name="extracted_frames.zip",
                                mime="application/zip"
                            )
                    
                    # Clean up temporary files
                    os.unlink(tmp_file_path)
                    
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
            else:
                st.warning("Please upload a video file first.")
    else:
        st.info("👆 Upload a video file to get started!")

with col2:
    st.header("💡 Tips & Information")
    
    st.markdown("""
    ### 🎯 **FPS Guidelines:**
    - **0.1-1.0 FPS**: Perfect for time-lapse effects
    - **1-10 FPS**: Good for slow-motion analysis
    - **10-30 FPS**: Ideal for detailed frame-by-frame review
    - **30+ FPS**: For high-speed motion analysis
    
    ### 🔧 **How It Works:**
    1. Upload your video file
    2. Set your desired extraction FPS
    3. Click "Extract Frames"
    4. Download the ZIP file with all frames
    
    ### 📁 **Output:**
    - All frames saved as high-quality JPG images
    - Organized in a downloadable ZIP archive
    - Frame naming: `frame_000001.jpg`, `frame_000002.jpg`, etc.
    
    ### ⚠️ **Note:**
    - Processing time depends on video length and target FPS
    - If target FPS > video FPS, all available frames will be extracted
    - The app automatically handles video metadata inconsistencies
    """)

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit | Video processing powered by OpenCV") 
