use eframe::egui;
use std::process::Command;

const PYTHON_EXECUTABLE: &str = "python3";
fn main() -> Result<(), eframe::Error> {
    eframe::run_native(
        "Alfa Developers Qualification",
        eframe::NativeOptions::default(),
        Box::new(|_cc| Ok(Box::new(MyApp::default()))),
    )
}

#[derive(Default)]
struct MyApp {
    start_date: String,
    end_date: String,
    link: String,
    result: String,
}

impl eframe::App for MyApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        let mut style = (*ctx.style()).clone();
        style.text_styles = [
            (
                egui::TextStyle::Heading,
                egui::FontId::new(30.0, egui::FontFamily::Proportional),
            ),
            (
                egui::TextStyle::Body,
                egui::FontId::new(17.0, egui::FontFamily::Proportional),
            ),
            (
                egui::TextStyle::Button,
                egui::FontId::new(17.0, egui::FontFamily::Proportional),
            ),
            (
                egui::TextStyle::Monospace,
                egui::FontId::new(17.0, egui::FontFamily::Monospace),
            ),
        ]
        .into();

        style.visuals.widgets.noninteractive.corner_radius = egui::CornerRadius::same(8);
        style.visuals.widgets.inactive.corner_radius = egui::CornerRadius::same(8);
        style.visuals.widgets.hovered.corner_radius = egui::CornerRadius::same(8);
        style.visuals.widgets.active.corner_radius = egui::CornerRadius::same(8);

        ctx.set_style(style);

        egui::CentralPanel::default().show(ctx, |ui| {
            ui.add_space(20.0);
            ui.heading("Rate skills of specified developer.");
            ui.add_space(20.0);

            ui.group(|ui| {
                ui.style_mut().visuals.widgets.noninteractive.bg_fill =
                    egui::Color32::from_gray(240);
                ui.style_mut().visuals.widgets.noninteractive.corner_radius =
                    egui::CornerRadius::same(10);

                ui.vertical(|ui| {
                    ui.add_space(10.0);

                    ui.horizontal(|ui| {
                        ui.label("Start Date:");
                        ui.add(
                            egui::TextEdit::singleline(&mut self.start_date)
                                .hint_text("YYYY-MM-DD"),
                        );
                    });

                    ui.horizontal(|ui| {
                        ui.label("End Date:");
                        ui.add(
                            egui::TextEdit::singleline(&mut self.end_date).hint_text("YYYY-MM-DD"),
                        );
                    });
                    ui.add_space(10.0);

                    ui.horizontal(|ui| {
                        ui.label("Link:");
                        ui.add(
                            egui::TextEdit::singleline(&mut self.link)
                                .hint_text("Enter link to repository"),
                        );
                    });

                    if ui.button("Submit").clicked() {
                        if self.start_date.is_empty() {
                            self.result = "Start date is required.".to_string();
                            return;
                        }
                        if self.end_date.is_empty() {
                            self.result = "End date is required.".to_string();
                            return;
                        }
                        if self.link.is_empty() {
                            self.result = "Link is required.".to_string();
                            return;
                        }
                        if let Err(_) = url::Url::parse(&self.link) {
                            self.result = "Invalid URL.".to_string();
                            return;
                        }

                        self.result = execute(&self.start_date, &self.end_date, &self.link)
                    }
                });
            });

            ui.add_space(20.0);

            ui.group(|ui| {
                ui.style_mut().visuals.override_text_color = Some(egui::Color32::WHITE);
                ui.style_mut().visuals.widgets.noninteractive.bg_fill =
                    egui::Color32::from_rgb(50, 50, 50);
                ui.style_mut().visuals.widgets.noninteractive.corner_radius =
                    egui::CornerRadius::same(10);

                ui.with_layout(
                    egui::Layout::top_down_justified(egui::Align::Center),
                    |ui| {
                        egui::ScrollArea::vertical()
                            .auto_shrink([false; 2])
                            .show(ui, |ui| {
                                ui.add_sized(
                                    ui.available_size(), // Fill all available space
                                    egui::Label::new(&self.result),
                                );
                            });
                    },
                );
            });
        });
    }
}

fn execute(start_date: &str, end_date: &str, link: &str) -> String {
    let output = Command::new(PYTHON_EXECUTABLE)
        .arg("../back.py")
        .arg("--urls")
        .arg(link)
        .arg("--start-date")
        .arg(start_date)
        .arg("--end-date")
        .arg(end_date)
        .arg("--output")
        .arg("code_quality_report.rpt")
        .output()
        .expect("Failed to execute command");
    if output.status.success() {
        let content = std::fs::read_to_string("code_quality_report.rpt")
            .expect("Failed to read output file")
            .to_string();
        return content;
    } else {
        let content = output.stdout;
        let content = String::from_utf8_lossy(&content);
        return content.to_string();
    }
}
