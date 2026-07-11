#!/usr/bin/env python3
"""
Mac Desktop AI Widget - Native macOS floating chat window using PyObjC/Cocoa.
Queries Ollama at localhost:11434 for AI responses.
Toggle with Cmd+Shift+A global hotkey.
"""

import sys
import os
import json
import threading
import urllib.request
import urllib.error

import objc
from Cocoa import (
    NSApplication, NSApp, NSWindow, NSView, NSTextField, NSTextView,
    NSScrollView, NSButton, NSPopUpButton, NSColor, NSFont,
    NSMakeRect, NSBackingStoreBuffered, NSFloatingWindowLevel,
    NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
    NSBorderlessWindowMask, NSViewWidthSizable, NSViewHeightSizable,
    NSViewMinYMargin, NSViewMaxYMargin, NSBezelStyleRounded,
    NSTextFieldSquareBezel, NSApplicationActivationPolicyAccessory,
    NSEvent, NSKeyDownMask, NSCommandKeyMask, NSShiftKeyMask,
    NSScreen, NSTimer, NSRunLoop, NSDefaultRunLoopMode,
    NSAttributedString, NSForegroundColorAttributeName,
    NSFontAttributeName
)
from Foundation import NSObject, NSMakeSize, NSDictionary
from AppKit import NSStatusBar, NSMenu, NSMenuItem, NSImage

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"


class ChatDelegate(NSObject):
    """Handles text field delegate methods."""
    
    def init(self):
        self = objc.super(ChatDelegate, self).init()
        if self is None:
            return None
        self.widget = None
        return self
    
    def control_textView_doCommandBySelector_(self, control, textView, selector):
        if selector == b"insertNewline:":
            if self.widget:
                self.widget.sendMessage_(None)
            return True
        return False


class WidgetWindow(NSObject):
    """Main widget controller."""
    
    def init(self):
        self = objc.super(WidgetWindow, self).init()
        if self is None:
            return None
        self.messages = []
        self.current_model = DEFAULT_MODEL
        self.available_models = [DEFAULT_MODEL]
        self.is_streaming = False
        self.window = None
        self.chat_view = None
        self.input_field = None
        self.model_popup = None
        return self
    
    def createWindow(self):
        """Create the floating window."""
        screen = NSScreen.mainScreen()
        screen_frame = screen.visibleFrame()
        
        # Position at top-right corner
        w, h = 320, 420
        x = screen_frame.origin.x + screen_frame.size.width - w - 20
        y = screen_frame.origin.y + screen_frame.size.height - h - 20
        
        frame = NSMakeRect(x, y, w, h)
        style = (NSWindowStyleMaskTitled | NSWindowStyleMaskClosable |
                 NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable)
        
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, style, NSBackingStoreBuffered, False
        )
        self.window.setTitle_("AI Chat")
        self.window.setLevel_(NSFloatingWindowLevel)
        self.window.setOpaque_(False)
        self.window.setAlphaValue_(0.92)
        self.window.setBackgroundColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(
            0.1, 0.1, 0.15, 0.95
        ))
        self.window.setMinSize_(NSMakeSize(250, 300))
        self.window.setHasShadow_(True)
        
        content = self.window.contentView()
        content_frame = content.frame()
        cw = content_frame.size.width
        ch = content_frame.size.height
        
        # Model selector at top
        self.model_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(10, ch - 35, cw - 20, 25), False
        )
        self.model_popup.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        self.model_popup.addItemWithTitle_(DEFAULT_MODEL)
        self.model_popup.setTarget_(self)
        self.model_popup.setAction_(b"modelChanged:")
        content.addSubview_(self.model_popup)
        
        # Scrollable chat area
        scroll_frame = NSMakeRect(10, 45, cw - 20, ch - 85)
        scroll_view = NSScrollView.alloc().initWithFrame_(scroll_frame)
        scroll_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setBorderType_(0)
        scroll_view.setDrawsBackground_(False)
        
        self.chat_view = NSTextView.alloc().initWithFrame_(
            NSMakeRect(0, 0, scroll_frame.size.width, scroll_frame.size.height)
        )
        self.chat_view.setEditable_(False)
        self.chat_view.setSelectable_(True)
        self.chat_view.setDrawsBackground_(False)
        self.chat_view.setTextColor_(NSColor.whiteColor())
        self.chat_view.setFont_(NSFont.systemFontOfSize_(12))
        self.chat_view.setAutoresizingMask_(NSViewWidthSizable)
        
        scroll_view.setDocumentView_(self.chat_view)
        content.addSubview_(scroll_view)
        
        # Input field at bottom
        self.input_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(10, 10, cw - 70, 25)
        )
        self.input_field.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        self.input_field.setPlaceholderString_("Ask anything...")
        self.input_field.setBezelStyle_(NSTextFieldSquareBezel)
        self.input_field.setFont_(NSFont.systemFontOfSize_(12))
        self.input_field.setTextColor_(NSColor.whiteColor())
        self.input_field.setBackgroundColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.2, 0.2, 0.25, 1.0)
        )
        
        # Set delegate for Enter key
        self.delegate = ChatDelegate.alloc().init()
        self.delegate.widget = self
        self.input_field.setDelegate_(self.delegate)
        content.addSubview_(self.input_field)
        
        # Send button
        send_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(cw - 55, 10, 45, 25)
        )
        send_btn.setAutoresizingMask_(NSViewMinXMargin | NSViewMinYMargin)
        send_btn.setTitle_("Send")
        send_btn.setBezelStyle_(NSBezelStyleRounded)
        send_btn.setTarget_(self)
        send_btn.setAction_(b"sendMessage:")
        content.addSubview_(send_btn)
        
        self.window.makeKeyAndOrderFront_(None)
        
        # Add welcome message
        self.appendMessage_("AI", "Hello! I'm your desktop AI assistant. Ask me anything.\n")
        
        # Fetch available models
        threading.Thread(target=self.fetchModels, daemon=True).start()
    
    def modelChanged_(self, sender):
        """Handle model selection change."""
        idx = self.model_popup.indexOfSelectedItem()
        self.current_model = self.model_popup.titleOfSelectedItem()
    
    def sendMessage_(self, sender):
        """Send user message to Ollama."""
        text = self.input_field.stringValue()
        if not text or self.is_streaming:
            return
        
        self.input_field.setStringValue_("")
        self.appendMessage_("You", text + "\n")
        self.messages.append({"role": "user", "content": text})
        
        self.is_streaming = True
        threading.Thread(target=self.queryOllama, args=(text,), daemon=True).start()
    
    def queryOllama(self, prompt):
        """Query Ollama API with streaming."""
        try:
            payload = json.dumps({
                "model": self.current_model,
                "messages": self.messages[-10:],  # Keep last 10 messages for context
                "stream": True
            }).encode()
            
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            
            response_text = ""
            with urllib.request.urlopen(req, timeout=60) as resp:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    b"appendAIPrefix:", "AI: ", False
                )
                for line in resp:
                    if line:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            chunk = data["message"]["content"]
                            response_text += chunk
                            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                                b"appendChunk:", chunk, False
                            )
                        if data.get("done"):
                            break
            
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                b"appendChunk:", "\n\n", False
            )
            self.messages.append({"role": "assistant", "content": response_text})
            
        except Exception as e:
            error_msg = f"\n[Error: {str(e)}]\n\n"
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                b"appendChunk:", error_msg, False
            )
        finally:
            self.is_streaming = False
    
    def appendAIPrefix_(self, prefix):
        """Append AI prefix on main thread."""
        storage = self.chat_view.textStorage()
        attrs = NSDictionary.dictionaryWithObjects_forKeys_(
            [NSColor.cyanColor(), NSFont.boldSystemFontOfSize_(12)],
            [NSForegroundColorAttributeName, NSFontAttributeName]
        )
        attr_str = NSAttributedString.alloc().initWithString_attributes_(prefix, attrs)
        storage.appendAttributedString_(attr_str)
        self.chat_view.scrollRangeToVisible_(self.chat_view.selectedRange())
    
    def appendChunk_(self, chunk):
        """Append streaming chunk on main thread."""
        storage = self.chat_view.textStorage()
        attrs = NSDictionary.dictionaryWithObjects_forKeys_(
            [NSColor.whiteColor(), NSFont.systemFontOfSize_(12)],
            [NSForegroundColorAttributeName, NSFontAttributeName]
        )
        attr_str = NSAttributedString.alloc().initWithString_attributes_(chunk, attrs)
        storage.appendAttributedString_(attr_str)
        # Auto-scroll to bottom
        range_end = storage.length()
        self.chat_view.scrollRangeToVisible_((range_end, 0))
    
    def appendMessage_(self, sender_name, text):
        """Append a formatted message to chat."""
        storage = self.chat_view.textStorage()
        
        # Sender name in color
        color = NSColor.greenColor() if sender_name == "You" else NSColor.cyanColor()
        attrs = NSDictionary.dictionaryWithObjects_forKeys_(
            [color, NSFont.boldSystemFontOfSize_(12)],
            [NSForegroundColorAttributeName, NSFontAttributeName]
        )
        header = NSAttributedString.alloc().initWithString_attributes_(
            f"{sender_name}: ", attrs
        )
        storage.appendAttributedString_(header)
        
        # Message text
        attrs2 = NSDictionary.dictionaryWithObjects_forKeys_(
            [NSColor.whiteColor(), NSFont.systemFontOfSize_(12)],
            [NSForegroundColorAttributeName, NSFontAttributeName]
        )
        body = NSAttributedString.alloc().initWithString_attributes_(text, attrs2)
        storage.appendAttributedString_(body)
        
        # Auto-scroll
        range_end = storage.length()
        self.chat_view.scrollRangeToVisible_((range_end, 0))
    
    def fetchModels(self):
        """Fetch available models from Ollama."""
        try:
            req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                models = [m["name"] for m in data.get("models", [])]
                if models:
                    self.available_models = models
                    self.performSelectorOnMainThread_withObject_waitUntilDone_(
                        b"updateModelList:", models, False
                    )
        except Exception:
            pass
    
    def updateModelList_(self, models):
        """Update model popup on main thread."""
        self.model_popup.removeAllItems()
        for model in models:
            self.model_popup.addItemWithTitle_(model)
        # Select default if available
        if DEFAULT_MODEL in models:
            self.model_popup.selectItemWithTitle_(DEFAULT_MODEL)
        self.current_model = self.model_popup.titleOfSelectedItem()
    
    def toggleWindow(self):
        """Toggle window visibility."""
        if self.window.isVisible():
            self.window.orderOut_(None)
        else:
            self.window.makeKeyAndOrderFront_(None)


class AppDelegate(NSObject):
    """Application delegate."""
    
    def init(self):
        self = objc.super(AppDelegate, self).init()
        if self is None:
            return None
        self.widget = None
        return self
    
    def applicationDidFinishLaunching_(self, notification):
        """Set up the widget and global hotkey."""
        self.widget = WidgetWindow.alloc().init()
        self.widget.createWindow()
        
        # Register global hotkey: Cmd+Shift+A
        NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSKeyDownMask, self.handleGlobalKey_
        )
        NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            NSKeyDownMask, self.handleLocalKey_
        )
    
    def handleGlobalKey_(self, event):
        """Handle global key events."""
        if (event.modifierFlags() & NSCommandKeyMask and
            event.modifierFlags() & NSShiftKeyMask and
            event.charactersIgnoringModifiers().lower() == 'a'):
            self.widget.toggleWindow()
    
    def handleLocalKey_(self, event):
        """Handle local key events."""
        if (event.modifierFlags() & NSCommandKeyMask and
            event.modifierFlags() & NSShiftKeyMask and
            event.charactersIgnoringModifiers().lower() == 'a'):
            self.widget.toggleWindow()
            return None
        return event


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    
    print("AI Widget running. Cmd+Shift+A to toggle. Close window or Ctrl+C to quit.")
    app.run()


if __name__ == "__main__":
    main()
