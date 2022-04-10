
try:
    from pysync.EventFlow import event_flow, post_sync_options, error_report
    from pysync.ProcessedOptions import PATH
    from pysync.Functions import HandledpysyncException
    
except Exception as e:
    print("pysync failed to initialize")
    raise e

def main():
    timer = None
    try:
        timer = event_flow(PATH)
        
    except KeyboardInterrupt:
        post_sync_options(timer, False)    
    except HandledpysyncException:
        post_sync_options(timer, True)
    except Exception as e:
        error_report(e, "The following error occured unexpectedly:", full_text=True, raise_exception=False)
        post_sync_options(timer, True)

        
        
    
    