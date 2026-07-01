import asyncio
from pipelines.idea2video_pipeline import Idea2VideoPipeline


# SET YOUR OWN IDEA, USER REQUIREMENT, AND STYLE HERE
idea = \
    """
A professional female fitness instructor with black hair is teaching a workout class
in a modern gym with floor-to-ceiling glass windows overlooking a beautiful beach.
She demonstrates three different exercises with proper form, showing confidence and
expertise. Between exercises, she faces the camera with an encouraging smile, explaining
the key technique points to help the audience understand the proper form.
"""
user_requirement = \
    """
For adults, do not exceed 3 scenes. Each scene should be no more than 5 shots.
"""
style = "Realistic, warm feel"


async def main():
    pipeline = Idea2VideoPipeline.init_from_config(
        config_path="configs/idea2video.yaml")
    await pipeline(idea=idea, user_requirement=user_requirement, style=style)

if __name__ == "__main__":
    asyncio.run(main())
