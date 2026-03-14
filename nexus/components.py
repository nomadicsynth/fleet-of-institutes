import gradio as gr

from data import DataManager

def create_feed_display(data_manager):
    def get_feed():
        papers = data_manager.get_papers()
        return [
            [
                paper[0],  # ID
                paper[1],  # Title
                paper[2],  # Author
                paper[3],  # Summary
                paper[4],  # Content
                paper[5],  # Tags
                paper[6],  # References
                paper[7]   # Timestamp
            ]
            for paper in papers
        ]

    with gr.Tab("Feed") as feed_tab:
        gr.Markdown("## Publication Feed")
        feed_table = gr.Dataframe(value=get_feed, headers=["ID", "Title", "Author", "Summary", "Content", "Tags", "References", "Timestamp"], interactive=False)

    return feed_tab, feed_table

def create_submission_form(data_manager: DataManager, feed_table: gr.Dataframe):
    def submit_paper(title, author, summary, content, tags, paper_references):
        from datetime import datetime
        timestamp = datetime.now().isoformat()
        data_manager.add_paper(title, author, summary, content, tags, paper_references, timestamp)
        updated_feed = [
            [
                paper[0],  # ID
                paper[1],  # Title
                paper[2],  # Author
                paper[3],  # Summary
                paper[4],  # Content
                paper[5],  # Tags
                paper[6],  # References
                paper[7]   # Timestamp
            ]
            for paper in data_manager.get_papers()
        ]
        return updated_feed, "Paper submitted successfully!"

    with gr.Tab("Submit Paper"):
        gr.Markdown("## Submit a New Paper")
        with gr.Row():
            title = gr.Textbox(label="Title")
            author = gr.Textbox(label="Author")
        summary = gr.Textbox(label="Summary")
        content = gr.Textbox(label="Content", lines=5)
        tags = gr.Textbox(label="Tags (comma-separated)")
        paper_references = gr.Textbox(label="References")
        submit_button = gr.Button("Submit")
        submit_button.click(
            submit_paper,
            inputs=[title, author, summary, content, tags, paper_references],
            outputs=[feed_table, gr.Textbox(label="Submission Status")]
        )